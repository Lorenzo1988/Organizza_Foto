"""
ExportAgent — Fase 5, step 32
Copia la struttura organizzata in una cartella di export.
GPS + XMP stripping obbligatorio prima di ogni copia.
"""
import logging
import os
import shutil
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class ExportAgent:
    """
    Copia l'intera struttura organizzata in una cartella di export.
    GPS e XMP stripping obbligatorio su ogni foto esportata.
    """

    def __init__(self, path_guard, audit_logger,
                 gps_stripper=None, xmp_stripper=None):
        self.path_guard = path_guard
        self.audit_logger = audit_logger
        self.gps_stripper = gps_stripper
        self.xmp_stripper = xmp_stripper

    def export_to_folder(self, source: str, dest: str) -> int:
        """
        Copia tutti i file dalla struttura source in dest.
        Ritorna il numero di file copiati.
        """
        if not os.path.isdir(source):
            logger.warning("ExportAgent: source non trovata: %s", source)
            return 0

        self.path_guard.add_allowed_root(dest)
        os.makedirs(dest, exist_ok=True)

        count = 0
        for root, dirs, files in os.walk(source):
            # Calcola il path relativo
            rel_root = os.path.relpath(root, source)
            dest_root = self.path_guard.safe_join(dest, rel_root) if rel_root != '.' else dest
            os.makedirs(dest_root, exist_ok=True)

            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext not in config.PHOTO_EXTENSIONS:
                    continue

                src_path = os.path.join(root, filename)
                dst_path = self.path_guard.safe_join(dest_root, filename)

                # Risolvi conflitti nome
                if os.path.exists(dst_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dst_path):
                        dst_path = self.path_guard.safe_join(
                            dest_root, f"{base}_{counter}{ext}"
                        )
                        counter += 1

                # AuditLogger PRIMA della copia
                self.audit_logger.log_copy(src_path, dst_path)

                # GPS + XMP stripping obbligatorio
                copied = False
                if self.gps_stripper is not None:
                    try:
                        self.gps_stripper.strip_gps(src_path, dst_path)
                        copied = True
                    except Exception as e:
                        logger.debug("Export GPS strip error: %s", e)

                if not copied and self.xmp_stripper is not None:
                    try:
                        self.xmp_stripper.strip_xmp(src_path, dst_path)
                        copied = True
                    except Exception as e:
                        logger.debug("Export XMP strip error: %s", e)

                if not copied:
                    shutil.copy2(src_path, dst_path)

                count += 1

        logger.debug("ExportAgent: copiati %d file in %s", count, dest)
        return count
