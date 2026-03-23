"""
AuditLoggerAgent v2 — Fase 2, step 6
Log immutabile append-only in formato JSON strutturato.
- Rotazione automatica a 5MB (max 3 file storici)
- Path assoluti ridotti a hash (no PII nel log)
- Thread-safe
"""
import json
import hashlib
import threading
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)


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

        # Rimuovi handler duplicati
        self._logger.handlers.clear()

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
            'ts': datetime.now(timezone.utc).isoformat(),
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
            try:
                self._logger.info(json.dumps(entry, ensure_ascii=False))
            except Exception as e:
                logger.error("AuditLogger: errore scrittura entry: %s", e)

    def _file_hash(self, path: str) -> str:
        """Hash MD5 dei primi 64KB del file per identificazione rapida."""
        try:
            h = hashlib.md5()
            with open(path, 'rb') as f:
                h.update(f.read(65536))
            return h.hexdigest()[:12]  # Abbreviato per leggibilità
        except Exception:
            return 'error'
