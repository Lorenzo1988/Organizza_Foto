# SECURITY_AUDIT.md — Analisi Completa di Sicurezza

Documento generato dopo analisi sistematica di tutti i file del progetto.
Stato: **16 problemi trovati**, di cui 8 già coperti dal pacchetto precedente,
8 nuovi da aggiungere.

---

## Riepilogo stato copertura

| # | Problema | File | Gravità | Stato |
|---|---|---|---|---|
| 1 | Path traversal via `highlight_name` | `folder_manager.py:107` | ALTA | ✅ Coperto (PathGuardAgent) |
| 2 | EXIF grezzo senza whitelist | `file_utils.py:70` | ALTA | ✅ Coperto (ExifSanitizerAgent) |
| 3 | File masquerading (solo estensione) | `file_utils.py:17` | ALTA | ✅ Coperto (FileValidatorAgent) |
| 4 | Move senza backup | `folder_manager.py:93` | ALTA | ✅ Coperto (FolderManagerAgent) |
| 5 | Checkpoint injection | `photo_manager.py:27` | MEDIA | ✅ Coperto (CheckpointManagerAgent) |
| 6 | Nessun audit trail | `main.py`, `folder_manager.py` | MEDIA | ✅ Coperto (AuditLoggerAgent) |
| 7 | Credenziali hardcoded in `config.py` | `config.py:4-5` | ALTA | ✅ Coperto (CredentialGuardAgent) |
| 8 | GPS nelle foto condivise | `file_utils.py` | MEDIA | ✅ Coperto (GpsStripperAgent) |
| 9 | **Nessuna autenticazione** | `main.py` | ALTA | ❌ **MANCANTE** |
| 10 | **Debug print in produzione** | `main_window.py:228` | BASSA | ❌ **MANCANTE** |
| 11 | **Delete senza cestino** | `main_window.py:404` | ALTA | ❌ **MANCANTE** |
| 12 | **Input senza rate limiting** | `main_window.py:302` | MEDIA | ❌ **MANCANTE** |
| 13 | **Sessione senza timeout** | `main_window.py` | MEDIA | ❌ **MANCANTE** |
| 14 | **Checkpoint non cifrato** | `photo_manager.py` | BASSA | ❌ **MANCANTE** |
| 15 | **os.remove senza audit** | `main_window.py:404`, `photo_manager.py:75` | MEDIA | ❌ **MANCANTE** (parziale) |
| 16 | **Copia senza verifica MD5** | `file_utils.py:103` | MEDIA | ❌ **MANCANTE** (parziale) |

---

## Problemi nuovi da risolvere

### 9. Nessuna autenticazione — `main.py`

**Problema**: chiunque apra l'applicazione ha accesso immediato a tutte le foto
e può eliminarle, spostarle, creare highlight. Non esiste alcun meccanismo
di autenticazione o PIN.

**Soluzione**: `AuthenticationAgent` con PIN locale hashato (bcrypt).

```python
# agents/security/auth_agent.py

import hashlib, os, getpass
from pathlib import Path

class AuthenticationAgent:
    """
    Gestisce autenticazione locale con PIN hashato.
    Il PIN non viene mai salvato in chiaro.
    """
    PIN_FILE = '.auth_hash'          # salvato nella cartella app, non committato
    MAX_ATTEMPTS = 3
    LOCKOUT_SECONDS = 300            # 5 minuti dopo 3 tentativi falliti
    SESSION_TIMEOUT_SECONDS = 3600   # 1 ora di inattività

    def __init__(self, app_dir: str):
        self.app_dir = app_dir
        self.pin_path = Path(app_dir) / self.PIN_FILE
        self._session_start = None
        self._last_activity = None
        self._failed_attempts = 0
        self._lockout_until = None

    def is_first_run(self) -> bool:
        return not self.pin_path.exists()

    def setup_pin(self, pin: str) -> bool:
        """Primo avvio: crea il PIN. Ritorna True se creato."""
        if len(pin) < 4:
            return False
        hashed = self._hash_pin(pin)
        self.pin_path.write_text(hashed)
        return True

    def authenticate(self, pin: str) -> bool:
        """Verifica il PIN. Gestisce tentativi falliti e lockout."""
        if self._is_locked_out():
            remaining = int((self._lockout_until - time.time()))
            raise PermissionError(f"Account bloccato. Riprova tra {remaining} secondi.")

        stored = self.pin_path.read_text().strip()
        if self._hash_pin(pin) == stored:
            self._failed_attempts = 0
            self._session_start = time.time()
            self._last_activity = time.time()
            return True
        else:
            self._failed_attempts += 1
            if self._failed_attempts >= self.MAX_ATTEMPTS:
                import time
                self._lockout_until = time.time() + self.LOCKOUT_SECONDS
            return False

    def is_session_valid(self) -> bool:
        """Verifica che la sessione non sia scaduta."""
        import time
        if self._last_activity is None:
            return False
        return (time.time() - self._last_activity) < self.SESSION_TIMEOUT_SECONDS

    def refresh_session(self):
        """Aggiorna il timestamp di ultima attività."""
        import time
        self._last_activity = time.time()

    def logout(self):
        self._session_start = None
        self._last_activity = None

    def change_pin(self, old_pin: str, new_pin: str) -> bool:
        if not self.authenticate(old_pin):
            return False
        return self.setup_pin(new_pin)

    def _hash_pin(self, pin: str) -> str:
        """SHA-256 con salt fisso derivato dalla macchina (non bcrypt per semplicità)."""
        import hashlib, uuid
        machine_id = str(uuid.getnode())  # MAC address come salt
        return hashlib.sha256(f"{pin}{machine_id}".encode()).hexdigest()

    def _is_locked_out(self) -> bool:
        import time
        if self._lockout_until is None:
            return False
        if time.time() > self._lockout_until:
            self._lockout_until = None
            self._failed_attempts = 0
            return False
        return True
```

**Flusso di autenticazione in `main.py`**:

```python
auth = AuthenticationAgent(app_dir=os.path.dirname(__file__))

if auth.is_first_run():
    # Prima esecuzione: mostra dialog setup PIN
    show_pin_setup_dialog(auth)
else:
    # Esecuzioni successive: mostra dialog login
    if not show_login_dialog(auth):
        sys.exit(0)  # Utente ha cancellato o troppi tentativi
```

**Aggiunta al `.gitignore`**:
```gitignore
.auth_hash
```

---

### 10. Debug print in produzione — `main_window.py:228`

**Problema**: tre `print(f"DEBUG - ...")` visibili a utenti e log di sistema.

```python
# CODICE VULNERABILE (main_window.py:228-233)
print(f"DEBUG - recent_highlights: {self.recent_highlights}")
print(f"DEBUG - all highlights: {highlights}")
print(f"DEBUG - recent_in_list: {recent_in_list}")
```

**Soluzione**: sostituire tutti i `print()` con il modulo `logging` configurato
a livello `WARNING` in produzione e `DEBUG` solo se `LOG_LEVEL=DEBUG` nel `.env`.

```python
import logging
logger = logging.getLogger(__name__)

# Invece di print(f"DEBUG - ...")
logger.debug("recent_highlights: %s", self.recent_highlights)
```

**Configurazione in `main.py`**:
```python
import logging, os
log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.WARNING))
```

---

### 11. Delete senza cestino — `main_window.py:404`

**Problema**: `os.remove(photo_path)` è irreversibile. Se l'utente elimina
per errore una foto, non c'è modo di recuperarla.

```python
# CODICE ORIGINALE — irreversibile
os.remove(photo_path)
```

**Soluzione**: spostare nel cestino di sistema con `send2trash`.

```python
# CODICE SICURO
from send2trash import send2trash
send2trash(photo_path)              # va nel cestino di sistema
audit_logger.log_delete(photo_path) # loggato come "trash"
```

**Dipendenza da aggiungere**:
```
send2trash>=1.8.2
```

---

### 12. Input senza rate limiting — `main_window.py:302`

**Problema**: `simpledialog.askstring()` per il nome highlight non ha validazione
di lunghezza né rate limiting. Un utente potrebbe inserire stringhe da MB.

```python
# CODICE ORIGINALE
name = simpledialog.askstring("Nuovo Highlight", "Nome del nuovo highlight:...")
if name:
    name = name.strip().replace('/', '_').replace('\\', '_')
    # Nessun controllo lunghezza, nessun rate limit
```

**Soluzione**: validazione in `PathGuardAgent.validate_highlight_name()` già prevista,
ma manca il collegamento dalla UI. Assicurarsi che la UI chiami sempre:

```python
if name:
    try:
        clean_name = path_guard.validate_highlight_name(name)
        self.move_to_highlight(clean_name, ...)
    except ValueError as e:
        messagebox.showerror("Nome non valido", str(e))
        return
```

---

### 13. Sessione senza timeout — `main_window.py`

**Problema**: una volta avviata la GUI, non c'è nessun meccanismo che
blocchi la sessione dopo inattività prolungata.

**Soluzione**: `AuthenticationAgent.is_session_valid()` (già nella spec sopra)
chiamato ogni 5 minuti tramite `root.after()`:

```python
# In UIAgent.__init__:
self.root.after(300_000, self._check_session_timeout)  # ogni 5 minuti

def _check_session_timeout(self):
    if not self.auth.is_session_valid():
        self._lock_screen()
    else:
        self.root.after(300_000, self._check_session_timeout)

def _lock_screen(self):
    """Mostra schermata di blocco."""
    # Nasconde il canvas, mostra dialog di re-autenticazione
    ...
```

---

### 14. Checkpoint non cifrato — `photo_manager.py`

**Problema**: `progress_checkpoint.txt` contiene path assoluti del filesystem
in chiaro. Se la cartella è sincronizzata su cloud, questi path sono esposti.

**Soluzione**: cifrare il file con `cryptography` (Fernet, chiave derivata dal PIN).

```python
# In CheckpointManagerAgent:
from cryptography.fernet import Fernet
import base64, hashlib

def _derive_key(self, pin_hash: str) -> bytes:
    """Deriva una chiave Fernet dal PIN hash."""
    return base64.urlsafe_b64encode(
        hashlib.sha256(pin_hash.encode()).digest()
    )
```

**Dipendenza** (opzionale, solo se si vuole cifratura):
```
cryptography>=42.0.0
```

**Nota**: se `cryptography` non è installato, il checkpoint rimane in chiaro
con un warning nel log. Non è un requisito bloccante.

---

### 15. os.remove senza audit — `main_window.py:404`, `photo_manager.py:75`

**Problema**: due `os.remove()` non passano per `AuditLoggerAgent`.

**File**: `main_window.py:404` (delete foto), `photo_manager.py:75` (clear progress)

**Soluzione**: iniettare `AuditLoggerAgent` in `UIAgent` e `CheckpointManagerAgent`
e sostituire ogni `os.remove()` con la sequenza:
```python
audit_logger.log_delete(path)
send2trash(path)  # o os.remove() per il checkpoint
```

---

### 16. Copia senza verifica MD5 — `file_utils.py:103`

**Problema**: `shutil.copy2()` non verifica che il file copiato sia identico
all'originale (disco pieno, errore I/O silenzioso).

**Soluzione**: già prevista in `FolderManagerAgent` con copy-then-verify,
ma `file_utils.py:copy_file_with_duplicate_handling()` va aggiornato:

```python
def copy_file_with_integrity_check(source_path: str, dest_folder: str) -> str:
    dest_path = _resolve_dest_path(source_path, dest_folder)
    shutil.copy2(source_path, dest_path)
    if _md5(source_path) != _md5(dest_path):
        os.remove(dest_path)
        raise IOError(f"Verifica integrità fallita: {source_path}")
    return dest_path

def _md5(path: str) -> str:
    import hashlib
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()
```

---

## Checklist finale — tutti i guardrail

### Security Gate (Layer 1)
- [x] FileValidatorAgent — magic bytes + dimensione + estensione
- [x] ExifSanitizerAgent — whitelist tag EXIF
- [x] PathGuardAgent — sandbox + traversal + validazione input
- [x] AuditLoggerAgent — log immutabile append-only
- [x] CredentialGuardAgent — nessuna credenziale hardcoded
- [x] GpsStripperAgent — rimozione GPS da foto pubbliche
- [ ] **AuthenticationAgent — PIN + lockout + session timeout** ← NUOVO
- [ ] **TrashAgent (send2trash) — delete reversibile** ← NUOVO

### Codice
- [x] Nessun shutil.move diretto → copy-verify-delete
- [x] Tutti i path via PathGuardAgent.safe_join()
- [ ] **Nessun print(DEBUG) — sostituire con logging** ← NUOVO
- [ ] **Tutti os.remove() via AuditLogger** ← fix parziale

### Dati
- [x] Percorsi da .env, mai hardcoded
- [x] .gitignore con .env, audit_log, checkpoint
- [x] GPS rimosso prima di HIGHLIGHTS e MIGLIORI_ANNO
- [ ] **Checkpoint cifrato (opzionale)** ← NUOVO

### Dipendenze da aggiungere
```
send2trash>=1.8.2        # cestino reversibile
cryptography>=42.0.0     # cifratura checkpoint (opzionale)
```
