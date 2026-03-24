# MONITORING.md — Logging Strutturato e Rilevamento Anomalie

Leggi questo file dopo SECURITY_AUDIT.md.
Copre i gap OWASP DA10 (Insufficient Logging & Monitoring).

---

## Gap nel logging attuale

L'AuditLogger attuale:
- Scrive in formato testo libero (difficile da parsare)
- Non ha rotazione del file (cresce senza limiti)
- Include path assoluti (PII esposto nel log)
- Non rileva pattern anomali (es. 50 delete in 5 minuti)
- Nessun alert all'utente per eventi critici

---

## AuditLoggerAgent v2 — log strutturato JSON

**File**: `agents/security/audit_logger.py` (sostituzione completa)

```python
import json
import hashlib
import threading
import time
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
import logging


class AuditLoggerAgent:
    """
    Log immutabile append-only in formato JSON strutturato.
    - Rotazione automatica a 5MB (max 3 file storici)
    - Path assoluti ridotti a hash (no PII nel log)
    - Thread-safe
    - Ogni entry ha: timestamp ISO, tipo, file_hash, nome_file, destinazione
    """

    MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
    BACKUP_COUNT = 3               # mantieni 3 file storici

    def __init__(self, log_path: str):
        self.log_path = log_path
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Configura RotatingFileHandler
        self._logger = logging.getLogger(f'audit.{id(self)}')
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        handler = RotatingFileHandler(
            log_path,
            maxBytes=self.MAX_BYTES,
            backupCount=self.BACKUP_COUNT,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(handler)

        self._write_entry('SESSION_START', detail='Applicazione avviata')

    # ── Operazioni filesystem ──────────────────────────────────────

    def log_move(self, src: str, dst: str):
        self._write_entry('MOVE', src=src, dst=dst)

    def log_copy(self, src: str, dst: str):
        self._write_entry('COPY', src=src, dst=dst)

    def log_delete(self, path: str):
        self._write_entry('DELETE', src=path)

    def log_skip(self, path: str, reason):
        if isinstance(reason, list):
            reason = '; '.join(str(r) for r in reason)
        self._write_entry('SKIP', src=path, detail=str(reason))

    def log_event(self, event: str, detail: str = ''):
        self._write_entry(event, detail=detail)

    # ── Interno ────────────────────────────────────────────────────

    def _write_entry(self, event_type: str, src: str = '',
                     dst: str = '', detail: str = ''):
        entry = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'type': event_type,
        }

        if src:
            # Salva solo nome file e hash — MAI il path assoluto
            entry['file'] = os.path.basename(src)
            entry['src_hash'] = self._file_hash(src)

        if dst:
            entry['dst_folder'] = os.path.basename(os.path.dirname(dst))

        if detail:
            entry['detail'] = detail[:500]  # Limita lunghezza

        with self._lock:
            self._logger.info(json.dumps(entry, ensure_ascii=False))

    def _file_hash(self, path: str) -> str:
        """Hash MD5 dei primi 64KB del file per identificazione rapida."""
        try:
            h = hashlib.md5()
            with open(path, 'rb') as f:
                h.update(f.read(65536))
            return h.hexdigest()[:12]  # Abbreviato per leggibilità
        except Exception:
            return 'error'
```

---

## AnomalyDetectorAgent — rilevamento pattern anomali

**File**: `agents/security/anomaly_detector.py`

```python
import time
from collections import deque
from typing import Callable


class AnomalyDetectorAgent:
    """
    Monitora il log degli eventi per pattern anomali e avvisa l'utente.
    Non blocca le operazioni: serve solo per allerta.

    Anomalie rilevate:
    - Troppe delete in poco tempo (possibile errore utente)
    - Tentativi ripetuti di path traversal
    - Accesso in orario insolito (opzionale)
    """

    # Soglie configurabili
    MAX_DELETES_PER_WINDOW = 20     # max 20 delete in DELETE_WINDOW secondi
    DELETE_WINDOW_SECONDS = 120     # finestra temporale 2 minuti
    MAX_TRAVERSAL_ATTEMPTS = 3      # max 3 tentativi di traversal

    def __init__(self, alert_callback: Callable[[str, str], None] = None):
        """
        alert_callback: funzione(tipo_anomalia, messaggio) chiamata quando
                        viene rilevata un'anomalia. Tipicamente mostra un
                        toast nella GUI.
        """
        self.alert_callback = alert_callback or (lambda t, m: print(f"⚠️ ANOMALIA [{t}]: {m}"))

        self._delete_timestamps: deque = deque()
        self._traversal_count: int = 0

    def on_delete(self, path: str):
        """Chiama ogni volta che viene eliminato un file."""
        now = time.time()
        self._delete_timestamps.append(now)

        # Rimuovi delete più vecchie della finestra temporale
        while self._delete_timestamps and \
              (now - self._delete_timestamps[0]) > self.DELETE_WINDOW_SECONDS:
            self._delete_timestamps.popleft()

        if len(self._delete_timestamps) >= self.MAX_DELETES_PER_WINDOW:
            self.alert_callback(
                'MASS_DELETE',
                f"{len(self._delete_timestamps)} file eliminati in "
                f"{self.DELETE_WINDOW_SECONDS // 60} minuti. "
                f"Controlla che non sia un errore."
            )

    def on_traversal_attempt(self, attempted_path: str):
        """Chiama ogni volta che PathGuard blocca un path traversal."""
        self._traversal_count += 1
        if self._traversal_count >= self.MAX_TRAVERSAL_ATTEMPTS:
            self.alert_callback(
                'PATH_TRAVERSAL',
                f"{self._traversal_count} tentativi di accesso a path non "
                f"autorizzati. Ultimo: {attempted_path[:50]}"
            )

    def on_auth_failure(self, attempt_number: int):
        """Chiama ad ogni PIN errato."""
        if attempt_number >= 2:
            self.alert_callback(
                'AUTH_FAILURE',
                f"Tentativo {attempt_number}/{3} di accesso con PIN errato."
            )

    def reset(self):
        self._delete_timestamps.clear()
        self._traversal_count = 0
```

### Integrazione in Orchestratore e UIAgent

```python
# In Orchestratore — connetti AnomalyDetector a PathGuard
def _on_path_guard_violation(self, path):
    self.anomaly_detector.on_traversal_attempt(path)
    self.audit_logger.log_event('PATH_TRAVERSAL_BLOCKED', path[:100])

# In UIAgent — connetti al tasto delete
def delete_photo(self):
    if messagebox.askyesno("Conferma", "Eliminare questa foto?"):
        photo_path = self.photo_manager.get_current_photo()
        self.anomaly_detector.on_delete(photo_path)  # ← aggiungi questa riga
        self.audit_logger.log_delete(photo_path)
        send2trash(photo_path)
        ...
```

---

## Formato log JSON (esempio)

```json
{"ts":"2025-10-12T14:23:01.123Z","type":"SESSION_START","detail":"Applicazione avviata"}
{"ts":"2025-10-12T14:23:05.456Z","type":"MOVE","file":"IMG_20240815.jpg","src_hash":"a1b2c3d4e5f6","dst_folder":"2024_Estate"}
{"ts":"2025-10-12T14:23:07.789Z","type":"COPY","file":"IMG_20240816.jpg","src_hash":"b2c3d4e5f6a1","dst_folder":"Vacanze_2024"}
{"ts":"2025-10-12T14:23:09.012Z","type":"SKIP","file":"IMG_corrupt.jpg","src_hash":"error","detail":"Magic bytes non validi"}
{"ts":"2025-10-12T14:23:11.345Z","type":"DELETE","file":"IMG_20240101.jpg","src_hash":"c3d4e5f6a1b2"}
{"ts":"2025-10-12T14:24:00.000Z","type":"CVE_FOUND","detail":"Pillow==10.0.0 CVE-2024-XXXXX"}
```

Nota: nessun path assoluto nel log — solo nome file e hash. Questo rispetta
GDPR (nessun percorso che riveli struttura cartelle personale) e OWASP DA3
(no sensitive info nei log).

---

## Test da aggiungere

**File**: `tests/test_monitoring.py`

```python
def test_audit_log_is_valid_json():
    # Ogni riga del log deve essere JSON valido

def test_audit_log_no_absolute_paths():
    # Nessuna riga deve contenere os.sep + percorso lungo

def test_audit_log_rotates_at_5mb():
    # Scrivi > 5MB → verifica che venga creato il file .1

def test_anomaly_mass_delete_triggered():
    # 20 delete in 2 minuti → alert_callback chiamato

def test_anomaly_not_triggered_below_threshold():
    # 19 delete in 2 minuti → nessun alert

def test_anomaly_traversal_alert():
    # 3 chiamate on_traversal_attempt() → alert_callback
```
