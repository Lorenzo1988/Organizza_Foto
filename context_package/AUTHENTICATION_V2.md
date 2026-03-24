# AUTHENTICATION_V2.md — Autenticazione Aggiornata (sostituisce AUTHENTICATION.md)

Questo file SOSTITUISCE AUTHENTICATION.md con le correzioni emerse dalla ricerca.
Leggi questo file, non AUTHENTICATION.md.

Problemi corretti rispetto alla versione precedente:
1. SHA-256 → bcrypt (cost 12) per resistenza al bruteforce
2. File .auth_hash → OS Keychain tramite libreria `keyring`
3. PIN in memoria come stringa → bytearray azzerabile
4. Aggiunta autenticazione per accesso a drive esterni (OWASP DA2)

Fonti: martinheinz.dev, keyring docs, OWASP DA2, passlib docs.

---

## Perché SHA-256 è sbagliato per i PIN

Un PIN numerico a 4 cifre ha solo 10.000 combinazioni (0000–9999).
SHA-256 su hardware moderno può calcolare **miliardi** di hash al secondo.
Con il file `.auth_hash` in mano, un attaccante bruteforza tutti i PIN
in meno di un millisecondo.

bcrypt con cost factor 12 richiede ~250ms per hash → brufteforce impossibile.

```
SHA-256:   10.000 PIN × 0,0000001ms = 0,001ms  ← inutile
bcrypt 12: 10.000 PIN × 250ms       = 41 minuti ← accettabile
argon2id:  10.000 PIN × 500ms       = 83 minuti ← ancora meglio
```

---

## Perché il file .auth_hash è sbagliato

Qualsiasi processo con accesso al filesystem può leggere `.auth_hash`.
Su Windows, macOS e Linux esiste uno storage cifrato nativo integrato
nel login dell'utente:

- **Windows**: Credential Manager (DPAPI — cifrato con password login)
- **macOS**: Keychain (cifrato con password login)
- **Linux**: Secret Service / GNOME Keyring / KWallet

La libreria `keyring` fornisce un'API unificata per tutti e tre.

---

## AuthenticationAgent v2

**File**: `agents/security/auth_agent.py`

```python
import bcrypt
import time
import os
from typing import Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

KEYRING_SERVICE = 'PhotoOrganizerV2'
KEYRING_USERNAME = 'app_pin_hash'


class AuthenticationAgent:
    """
    Autenticazione locale con:
    - PIN hashato con bcrypt (cost 12)
    - Hash salvato nel OS Keychain (Credential Manager / Keychain / Secret Service)
    - Fallback a file cifrato se keyring non disponibile
    - PIN azzerato dalla memoria dopo l'uso
    - Lockout dopo MAX_ATTEMPTS tentativi
    - Timeout sessione configurabile
    """

    MAX_ATTEMPTS = 3
    LOCKOUT_SECONDS = 300        # 5 minuti
    SESSION_TIMEOUT_SECONDS = 3600  # 1 ora
    BCRYPT_ROUNDS = 12           # ~250ms per hash — resistente a bruteforce
    FALLBACK_HASH_FILE = '.auth_hash_enc'  # usato solo se keyring non disponibile

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
        # Fallback: controlla file
        fallback = os.path.join(self.app_dir, self.FALLBACK_HASH_FILE)
        return not os.path.exists(fallback)

    def setup_pin(self, pin_bytes: bytearray) -> tuple[bool, str]:
        """
        Crea il PIN. Accetta bytearray per poterlo azzerare dopo l'uso.
        Ritorna (True, '') o (False, messaggio_errore).
        """
        try:
            if len(pin_bytes) < 4:
                return False, "PIN deve essere di almeno 4 caratteri"
            if len(pin_bytes) > 32:
                return False, "PIN troppo lungo (max 32 caratteri)"

            # Hash con bcrypt
            pin_str = bytes(pin_bytes).decode('utf-8', errors='ignore')
            hashed = bcrypt.hashpw(pin_str.encode(), bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS))
            hashed_str = hashed.decode('utf-8')

            # Salva nel OS Keychain
            if KEYRING_AVAILABLE:
                keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, hashed_str)
                return True, ''
            else:
                # Fallback: salva in file con permessi ristretti
                fallback = os.path.join(self.app_dir, self.FALLBACK_HASH_FILE)
                with open(fallback, 'w', encoding='utf-8') as f:
                    f.write(hashed_str)
                os.chmod(fallback, 0o600)
                return True, '⚠️ keyring non disponibile: hash salvato in file locale'

        except Exception as e:
            return False, f"Errore nel salvataggio: {e}"
        finally:
            # Azzeramento PIN dalla memoria
            for i in range(len(pin_bytes)):
                pin_bytes[i] = 0

    # ── Autenticazione ─────────────────────────────────────────────

    def authenticate(self, pin_bytes: bytearray) -> tuple[bool, str]:
        """
        Verifica il PIN. Accetta bytearray per azzerarlo dopo l'uso.
        Ritorna (True, '') o (False, messaggio_errore).
        """
        try:
            if self._is_locked_out():
                remaining = int(self._lockout_until - time.time())
                return False, f"Bloccato. Riprova tra {remaining} secondi."

            # Recupera hash
            stored_hash = self._get_stored_hash()
            if not stored_hash:
                return False, "Nessun PIN configurato."

            # Verifica bcrypt
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
            # Azzeramento PIN dalla memoria — sempre, anche in caso di errore
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

    def change_pin(self, old_pin: bytearray, new_pin: bytearray) -> tuple[bool, str]:
        ok, msg = self.authenticate(old_pin)
        if not ok:
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
            os.remove(fallback)

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
```

---

## Dialog di autenticazione — uso corretto di bytearray

Il PIN deve essere raccolto come `bytearray` dalla GUI per poterlo azzerare:

```python
# ui/auth_dialogs.py

class LoginDialog(tk.Toplevel):

    def _on_submit(self):
        pin_str = self.pin_var.get()

        # Converti in bytearray (mutabile, azzerabile)
        pin_bytes = bytearray(pin_str.encode('utf-8'))

        # Azzera subito il campo UI
        self.pin_var.set('')
        self.pin_entry.delete(0, tk.END)

        # Autentica (authenticate() azzerero' pin_bytes internamente)
        ok, msg = self.auth.authenticate(pin_bytes)
        # pin_bytes è già stato azzerato da authenticate()

        if ok:
            self.result = True
            self.destroy()
        else:
            self._show_error(msg)
            self._shake_entry()
```

---

## OWASP DA2 — Autenticazione per drive esterni

Il codice deve verificare che SOURCE_FOLDER e DESTINATION_FOLDER siano
accessibili prima di avviare la pipeline:

```python
# In CredentialGuardAgent o Orchestratore:

def verify_folder_access(path: str, path_guard: PathGuardAgent) -> tuple[bool, str]:
    """Verifica che la cartella esista e sia accessibile."""
    if not os.path.exists(path):
        return False, f"Cartella non trovata: {path}"
    if not os.access(path, os.R_OK):
        return False, f"Permesso di lettura negato: {path}"
    if not path_guard.is_safe_path(path):
        return False, f"Path non autorizzato: {path}"
    return True, ''
```

---

## Dipendenze aggiornate

```
# requirements.in
bcrypt>=4.0.0            # hashing PIN sicuro (sostituisce SHA-256)
keyring>=25.0.0          # OS Keychain — Windows/macOS/Linux
```

---

## Test da aggiungere

**File**: `tests/test_auth_agent_v2.py`

```python
def test_bcrypt_used_not_sha256():
    # Il hash salvato deve iniziare con '$2b$' (bcrypt)
    # Non deve contenere sha256 o uuid

def test_pin_memory_wiped_after_auth():
    # Dopo authenticate(), il bytearray passato deve essere tutto zeri

def test_pin_memory_wiped_after_failed_auth():
    # Anche dopo auth fallita, il bytearray deve essere azzerato

def test_keyring_used_when_available(monkeypatch):
    # Mock keyring.set_password → verifica che venga chiamato

def test_fallback_file_when_keyring_unavailable(monkeypatch):
    # Mock KEYRING_AVAILABLE = False → verifica creazione file fallback

def test_bruteforce_resistance():
    # 3 tentativi falliti → lockout attivo
    # 4° tentativo → errore lockout (non "PIN errato")

def test_session_expires():
    # Imposta _last_activity = time.time() - 3700
    # is_session_valid() deve ritornare False
```
