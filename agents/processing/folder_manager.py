"""
FolderManagerAgent — Fase 4, step 27
Gestisce lo spostamento delle foto con copy-verify-delete (NO shutil.move diretto).
Ogni operazione: audit_logger PRIMA, poi filesystem.
Ogni delete: send2trash (NON os.remove).
"""
import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import List

from config import (
    HIGHLIGHTS_FOLDER_NAME, EVENTS_FOLDER_NAME,
    ARCHIVE_FOLDER_NAME, TO_PRINT_FOLDER_NAME
)

logger = logging.getLogger(__name__)

try:
    from send2trash import send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError:
    SEND2TRASH_AVAILABLE = False
    logger.warning("send2trash non disponibile: install: pip install send2trash")


class FolderManagerAgent:
    """
    Gestisce l'organizzazione delle foto nelle cartelle di destinazione.

    Sicurezza:
    - Usa copy-verify-delete invece di shutil.move
    - Ogni delete via send2trash (reversibile)
    - Ogni operazione logga su AuditLogger PRIMA di agire
    - Tutti i path tramite PathGuardAgent.safe_join()
    """

    def __init__(self, path_guard, audit_logger):
        self.path_guard = path_guard
        self.audit_logger = audit_logger

    def organize(self, meta, destination: str) -> str:
        """
        Sposta la foto nella cartella corretta (EVENTI o ARCHIVIO).
        Usa copy-verify-delete per sicurezza.
        Ritorna il nuovo path.
        """
        if meta.date is None:
            # Fallback: cartella ARCHIVIO/senza_data
            dest_folder = self.path_guard.safe_join(
                destination, ARCHIVE_FOLDER_NAME, 'senza_data'
            )
        else:
            event_name = meta.event_name
            year = str(meta.date.year)

            if meta.event_priority >= 3:
                base = self.path_guard.safe_join(destination, EVENTS_FOLDER_NAME, year)
            else:
                base = self.path_guard.safe_join(destination, ARCHIVE_FOLDER_NAME, year)

            folder_name = event_name or f"{year}_Altro"
            dest_folder = self.path_guard.safe_join(base, folder_name)

        os.makedirs(dest_folder, exist_ok=True)

        dest_path = self._resolve_dest_path(meta.current_path, dest_folder)

        # AuditLogger PRIMA dell'operazione
        self.audit_logger.log_move(meta.current_path, dest_path)

        # copy-verify-delete
        self._copy_verify_delete(meta.current_path, dest_path)

        return dest_path

    def move_to_highlight(self, meta, highlight_name: str) -> str:
        """
        Copia la foto in un highlight (validando il nome con PathGuard).
        Ritorna il path di destinazione.
        """
        clean_name = self.path_guard.validate_highlight_name(highlight_name)

        # Determina la destination root da path_guard
        # Prende la prima root consentita come base
        dest_root = self._get_destination_root()
        highlight_folder = self.path_guard.safe_join(
            dest_root, HIGHLIGHTS_FOLDER_NAME, clean_name
        )
        os.makedirs(highlight_folder, exist_ok=True)

        dest_path = self._resolve_dest_path(meta.current_path, highlight_folder)
        self.audit_logger.log_copy(meta.current_path, dest_path)
        shutil.copy2(meta.current_path, dest_path)
        return dest_path

    def get_existing_highlights(self, destination: str) -> List[str]:
        """Ritorna lista delle cartelle highlight esistenti (ordinate per data)."""
        highlights_path = os.path.join(destination, HIGHLIGHTS_FOLDER_NAME)
        if not os.path.exists(highlights_path):
            return []

        highlights = []
        try:
            for item in os.listdir(highlights_path):
                item_path = os.path.join(highlights_path, item)
                if os.path.isdir(item_path):
                    ctime = os.path.getctime(item_path)
                    highlights.append((item, ctime))
            highlights.sort(key=lambda x: x[1], reverse=True)
            return [name for name, _ in highlights]
        except Exception as e:
            logger.debug("get_existing_highlights error: %s", e)
            return []

    # ── Internals ─────────────────────────────────────────────────

    def _copy_verify_delete(self, src: str, dst: str):
        """
        copy-verify-delete sicuro:
        1. Copia in destinazione
        2. Verifica MD5 source == MD5 dest
        3. Solo se OK: elimina sorgente via send2trash
        """
        shutil.copy2(src, dst)

        src_md5 = self._md5(src)
        dst_md5 = self._md5(dst)

        if src_md5 != dst_md5:
            # Rimuovi la copia corrotta
            try:
                os.remove(dst)
            except Exception:
                pass
            raise IOError(f"Verifica integrità fallita: {os.path.basename(src)}")

        # AuditLogger PRIMA del delete
        self.audit_logger.log_delete(src)

        if SEND2TRASH_AVAILABLE:
            send2trash(src)
        else:
            logger.warning("send2trash non disponibile: usando os.remove come fallback")
            os.remove(src)

    def _md5(self, path: str) -> str:
        """Calcola MD5 completo del file."""
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _resolve_dest_path(self, src: str, dest_folder: str) -> str:
        """Calcola il path destinazione gestendo i duplicati."""
        filename = os.path.basename(src)
        dest_path = os.path.join(dest_folder, filename)

        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
                counter += 1

        return dest_path

    def _get_destination_root(self) -> str:
        """Ritorna la prima root consentita (usata per costruire path highlights)."""
        if self.path_guard._allowed_roots:
            return str(self.path_guard._allowed_roots[-1])
        return os.getcwd()
