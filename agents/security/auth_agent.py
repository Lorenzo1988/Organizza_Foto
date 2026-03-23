"""
AuthenticationAgent v2 — Fase 2, step 11
Autenticazione locale con:
- PIN hashato con bcrypt (cost 12)
- Hash salvato nel OS Keychain (Credential Manager / Keychain / Secret Service)
- Fallback a file cifrato se keyring non disponibile
- PIN azzerato dalla memoria dopo l'uso (bytearray)
- Lockout dopo MAX_ATTEMPTS tentativi
- Timeout sessione configurabile
"""
import time
import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt non disponibile. Installa: pip install bcrypt")

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning("keyring non disponibile. Installa: pip install keyring")

KEYRING_SERVICE = 'PhotoOrganizerV2'
KEYRING_USERNAME = 'app_pin_hash'


class AuthenticationAgent:
    """
    Autenticazione locale con bcrypt (cost 12) e OS Keychain.
    Il PIN è accettato come bytearray per poterlo azzerare dopo l'uso.
    """

    MAX_ATTEMPTS = 3
    LOCKOUT_SECONDS = 300           # 5 minuti
    SESSION_TIMEOUT_SECONDS = 3600  # 1 ora
    BCRYPT_ROUNDS = 12              # ~250ms per hash
    FALLBACK_HASH_FILE = '.auth_hash_enc'

    def __init__(self, app_dir: str):
        self.app_dir = app_dir
        self._last_activity: Optional[float] = None
        self._failed_attempts: int = 0
        self._lockout_until: Optional[float] = None

    # ── Primo avvio ────────────────────────────────────────────────

    def is_first_run(self) -> bool:
        """True se non esiste ancora un PIN configurato."""
        if KEYRING_AVAILABLE:
            try:
                stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
                return stored is None
            except Exception:
                pass
        fallback = os.path.join(self.app_dir, self.FALLBACK_HASH_FILE)
        return not os.path.exists(fallback)

    def setup_pin(self, pin_bytes: bytearray) -> Tuple[bool, str]:
        """
        Crea il PIN. Accetta bytearray per poterlo azzerare dopo l'uso.
        Ritorna (True, '') o (False, messaggio_errore).
        """
        try:
            if len(pin_bytes) < 4:
                return False, "PIN deve essere di almeno 4 caratteri"
            if len(pin_bytes) > 32:
                return False, "PIN troppo lungo (max 32 caratteri)"

            if not BCRYPT_AVAILABLE:
                return False, "bcrypt non disponibile. Installa: pip install bcrypt"

            pin_str = bytes(pin_bytes).decode('utf-8', errors='ignore')
            hashed = bcrypt.hashpw(pin_str.encode(), bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS))
            hashed_str = hashed.decode('utf-8')

            if KEYRING_AVAILABLE:
                keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, hashed_str)
                return True, ''
            else:
                fallback = os.path.join(self.app_dir, self.FALLBACK_HASH_FILE)
                with open(fallback, 'w', encoding='utf-8') as f:
                    f.write(hashed_str)
                try:
                    os.chmod(fallback, 0o600)
                except Exception:
                    pass
                return True, 'keyring non disponibile: hash salvato in file locale'

        except Exception as e:
            return False, f"Errore nel salvataggio: {e}"
        finally:
            for i in range(len(pin_bytes)):
                pin_bytes[i] = 0

    # ── Autenticazione ─────────────────────────────────────────────

    def authenticate(self, pin_bytes: bytearray) -> Tuple[bool, str]:
        """
        Verifica il PIN. Accetta bytearray per azzerarlo dopo l'uso.
        Ritorna (True, '') o (False, messaggio_errore).
        """
        try:
            if self._is_locked_out():
                remaining = int(self._lockout_until - time.time())
                return False, f"Bloccato. Riprova tra {remaining} secondi."

            stored_hash = self._get_stored_hash()
            if not stored_hash:
                return False, "Nessun PIN configurato."

            if not BCRYPT_AVAILABLE:
                return False, "bcrypt non disponibile."

            pin_str = bytes(pin_bytes).decode('utf-8', errors='ignore')
            is_valid = bcrypt.checkpw(pin_str.encode(), stored_hash.encode())

            if is_valid:
                self._failed_attempts = 0
                self._lockout_until = None
                self._last_activity = time.time()
                return True, ''
            else:
                self._failed_attempts += 1
                if self._failed_attempts >= self.MAX_ATTEMPTS:
                    self._lockout_until = time.time() + self.LOCKOUT_SECONDS
                    return False, f"Troppi tentativi. Bloccato per {self.LOCKOUT_SECONDS // 60} min."
                remaining = self.MAX_ATTEMPTS - self._failed_attempts
                return False, f"PIN errato. Tentativi rimanenti: {remaining}"

        except Exception as e:
            return False, f"Errore di autenticazione: {e}"
        finally:
            for i in range(len(pin_bytes)):
                pin_bytes[i] = 0

    # ── Sessione ───────────────────────────────────────────────────

    def is_session_valid(self) -> bool:
        if self._last_activity is None:
            return False
        return (time.time() - self._last_activity) < self.SESSION_TIMEOUT_SECONDS

    def refresh_session(self):
        if self._last_activity is not None:
            self._last_activity = time.time()

    def logout(self):
        self._last_activity = None

    def get_session_remaining_minutes(self) -> int:
        if not self.is_session_valid():
            return 0
        elapsed = time.time() - self._last_activity
        return max(0, int((self.SESSION_TIMEOUT_SECONDS - elapsed) / 60))

    # ── Cambio PIN ─────────────────────────────────────────────────

    def change_pin(self, old_pin: bytearray, new_pin: bytearray) -> Tuple[bool, str]:
        ok, msg = self.authenticate(old_pin)
        # old_pin già azzerato da authenticate()
        if not ok:
            # new_pin deve essere azzerato manualmente
            for i in range(len(new_pin)):
                new_pin[i] = 0
            return False, f"PIN attuale errato: {msg}"
        return self.setup_pin(new_pin)

    def reset_pin(self):
        """Elimina il PIN (richiede accesso fisico al dispositivo)."""
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
            except Exception:
                pass
        fallback = os.path.join(self.app_dir, self.FALLBACK_HASH_FILE)
        if os.path.exists(fallback):
            try:
                os.remove(fallback)
            except Exception:
                pass

    # ── Interno ────────────────────────────────────────────────────

    def _get_stored_hash(self) -> Optional[str]:
        if KEYRING_AVAILABLE:
            try:
                return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            except Exception:
                pass
        fallback = os.path.join(self.app_dir, self.FALLBACK_HASH_FILE)
        if os.path.exists(fallback):
            with open(fallback, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return None

    def _is_locked_out(self) -> bool:
        if self._lockout_until is None:
            return False
        if time.time() > self._lockout_until:
            self._lockout_until = None
            self._failed_attempts = 0
            return False
        return True
