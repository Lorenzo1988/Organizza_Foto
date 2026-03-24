# AUTHENTICATION.md — Gestione Autenticazione

Leggi questo file DOPO SECURITY_AUDIT.md.
Implementa `AuthenticationAgent` PRIMA di avviare la GUI.

---

## Flusso completo di autenticazione

```
Avvio app
    │
    ▼
CredentialGuardAgent.check()  ← blocca se credenziali hardcoded
    │
    ▼
AuthenticationAgent.is_first_run()?
    ├── SÌ → PinSetupDialog → setup_pin() → salva hash
    └── NO → LoginDialog
                │
                ├── PIN corretto → sessione avviata → GUI
                ├── PIN errato (1-2 volte) → riprova
                └── PIN errato (3 volte) → lockout 5 min
                                               │
                                               └── dopo 5 min → torna a LoginDialog

Durante la GUI:
    └── ogni 5 min → check session_timeout (1 ora inattività)
                         └── scaduta → LockScreen → re-autenticazione
```

---

## AuthenticationAgent

**File**: `agents/security/auth_agent.py`

```python
import hashlib, os, time, uuid
from pathlib import Path


class AuthenticationAgent:
    PIN_FILE = '.auth_hash'
    MAX_ATTEMPTS = 3
    LOCKOUT_SECONDS = 300        # 5 minuti
    SESSION_TIMEOUT_SECONDS = 3600  # 1 ora

    def __init__(self, app_dir: str):
        self.app_dir = Path(app_dir)
        self.pin_path = self.app_dir / self.PIN_FILE
        self._last_activity: float | None = None
        self._failed_attempts: int = 0
        self._lockout_until: float | None = None

    # ── Setup ──────────────────────────────────────────────────────

    def is_first_run(self) -> bool:
        return not self.pin_path.exists()

    def setup_pin(self, pin: str) -> tuple[bool, str]:
        """
        Primo avvio: crea il PIN.
        Ritorna (True, '') o (False, messaggio_errore).
        """
        if not pin or not isinstance(pin, str):
            return False, "PIN non può essere vuoto"
        if len(pin) < 4:
            return False, "PIN deve essere di almeno 4 caratteri"
        if len(pin) > 32:
            return False, "PIN troppo lungo (max 32 caratteri)"
        try:
            hashed = self._hash_pin(pin)
            self.pin_path.write_text(hashed, encoding='utf-8')
            self.pin_path.chmod(0o600)  # solo il proprietario può leggere
            return True, ''
        except Exception as e:
            return False, f"Errore nel salvataggio: {e}"

    # ── Autenticazione ─────────────────────────────────────────────

    def authenticate(self, pin: str) -> tuple[bool, str]:
        """
        Verifica il PIN.
        Ritorna (True, '') o (False, messaggio_errore).
        """
        # Check lockout
        if self._is_locked_out():
            remaining = int(self._lockout_until - time.time())
            return False, f"Troppi tentativi. Riprova tra {remaining} secondi."

        if not self.pin_path.exists():
            return False, "Nessun PIN configurato. Esegui il setup."

        try:
            stored = self.pin_path.read_text(encoding='utf-8').strip()
        except Exception:
            return False, "Errore nella lettura del PIN."

        if self._hash_pin(pin) == stored:
            self._failed_attempts = 0
            self._lockout_until = None
            self._last_activity = time.time()
            return True, ''
        else:
            self._failed_attempts += 1
            if self._failed_attempts >= self.MAX_ATTEMPTS:
                self._lockout_until = time.time() + self.LOCKOUT_SECONDS
                return False, (
                    f"Troppi tentativi ({self.MAX_ATTEMPTS}/{self.MAX_ATTEMPTS}). "
                    f"Account bloccato per {self.LOCKOUT_SECONDS // 60} minuti."
                )
            remaining_attempts = self.MAX_ATTEMPTS - self._failed_attempts
            return False, f"PIN errato. Tentativi rimanenti: {remaining_attempts}"

    # ── Sessione ───────────────────────────────────────────────────

    def is_session_valid(self) -> bool:
        if self._last_activity is None:
            return False
        return (time.time() - self._last_activity) < self.SESSION_TIMEOUT_SECONDS

    def refresh_session(self):
        """Chiama questo ad ogni interazione utente per resettare il timeout."""
        if self._last_activity is not None:
            self._last_activity = time.time()

    def get_session_remaining_seconds(self) -> int:
        if self._last_activity is None:
            return 0
        elapsed = time.time() - self._last_activity
        remaining = self.SESSION_TIMEOUT_SECONDS - elapsed
        return max(0, int(remaining))

    def logout(self):
        self._last_activity = None

    # ── Cambio PIN ─────────────────────────────────────────────────

    def change_pin(self, old_pin: str, new_pin: str) -> tuple[bool, str]:
        ok, msg = self.authenticate(old_pin)
        if not ok:
            return False, f"PIN attuale errato: {msg}"
        return self.setup_pin(new_pin)

    def reset_pin(self):
        """Elimina il PIN (richiede accesso fisico alla cartella app)."""
        if self.pin_path.exists():
            self.pin_path.unlink()

    # ── Interno ────────────────────────────────────────────────────

    def _hash_pin(self, pin: str) -> str:
        """SHA-256 con salt derivato dall'ID macchina."""
        machine_id = str(uuid.getnode())
        return hashlib.sha256(f"{pin}{machine_id}{len(pin)}".encode()).hexdigest()

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

## Dialog di autenticazione (tkinter)

**File**: `ui/auth_dialogs.py`

Implementa questi tre dialog come finestre tkinter modali (stile `Toplevel`
con `grab_set()` e design coerente con il resto dell'app):

### PinSetupDialog

Mostrato solo al primo avvio. Chiede:
- PIN (campo password, caratteri nascosti)
- Conferma PIN
- Bottone "Crea PIN"

Validazione lato UI:
- I due PIN devono coincidere
- Lunghezza minima 4 caratteri
- Mostra indicatore di forza (debole/medio/forte) in base a lunghezza e varietà caratteri

### LoginDialog

Mostrato ad ogni avvio e dopo il lockout del timeout sessione. Mostra:
- Logo/icona dell'app
- Campo PIN (caratteri nascosti, autofocus)
- Bottone "Accedi"
- Messaggio di errore sotto il campo (rosso, visibile solo dopo tentativo fallito)
- Indicatore tentativi rimanenti
- Pulsante "?" per istruzioni reset PIN

### LockScreenDialog

Mostrato dopo timeout sessione. Sovrappone la GUI esistente:
- Overlay semitrasparente scuro sull'intera finestra
- Card centrale con logo + campo PIN + bottone "Sblocca"
- Pulsante "Esci" che chiude completamente l'app

---

## Integrazione in main.py

```python
# main.py — sezione autenticazione (da aggiungere PRIMA di tutto)

import tkinter as tk
from agents.security.auth_agent import AuthenticationAgent
from ui.auth_dialogs import PinSetupDialog, LoginDialog

def run_auth_flow(auth: AuthenticationAgent) -> bool:
    """
    Gestisce il flusso di autenticazione.
    Ritorna True se autenticato, False se l'utente ha annullato.
    """
    root_auth = tk.Tk()
    root_auth.withdraw()  # Nasconde la finestra temporanea

    if auth.is_first_run():
        dialog = PinSetupDialog(root_auth, auth)
        root_auth.wait_window(dialog)
        success = dialog.result
    else:
        dialog = LoginDialog(root_auth, auth)
        root_auth.wait_window(dialog)
        success = dialog.result

    root_auth.destroy()
    return success

def main():
    auth = AuthenticationAgent(app_dir=os.path.dirname(os.path.abspath(__file__)))

    # 1. Controlla credenziali hardcoded
    credential_guard = CredentialGuardAgent()
    warnings = credential_guard.check_config('config.py')
    if warnings:
        for w in warnings:
            print(f"⚠️  SICUREZZA: {w}")

    env_errors = credential_guard.check_env_loaded(SOURCE_FOLDER, DESTINATION_FOLDER)
    if env_errors:
        for e in env_errors:
            print(f"❌ {e}")
        sys.exit(1)

    # 2. Autenticazione
    if not run_auth_flow(auth):
        print("Accesso annullato.")
        sys.exit(0)

    # 3. Avvia il resto dell'app con auth iniettato
    ...
```

---

## Aggiunta al .gitignore

```gitignore
.auth_hash
```

---

## Test da scrivere

**File**: `tests/test_auth_agent.py`

```python
def test_first_run_is_true_without_pin_file():
    ...

def test_setup_pin_too_short():
    # PIN di 3 caratteri → False

def test_authenticate_correct_pin():
    # Setup + authenticate con PIN corretto → True

def test_authenticate_wrong_pin():
    # Authenticate con PIN errato → False + messaggio

def test_lockout_after_max_attempts():
    # 3 tentativi falliti → lockout

def test_session_expires_after_timeout():
    # Simula inattività > SESSION_TIMEOUT → is_session_valid() False

def test_session_refresh_resets_timer():
    # refresh_session() → timer resettato
```
