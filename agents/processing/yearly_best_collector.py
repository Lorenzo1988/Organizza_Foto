"""
YearlyBestCollectorAgent — Fase 4, step 29
Raccoglie le migliori foto di ogni anno dagli HIGHLIGHTS.
Usa GpsStripperAgent + XmpStripperAgent prima di copiare.
"""
import logging
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import config

logger = logging.getLogger(__name__)


class YearlyBestCollectorAgent:
    """
    Raccoglie le migliori N foto per anno dagli HIGHLIGHTS.
    - Non sposta le originali — le COPIA
    - Idempotente: se la cartella esiste, aggiunge solo le mancanti
    - Stripping GPS + XMP prima di copiare (privacy)
    """

    def __init__(self, path_guard, audit_logger, count: int = None,
                 gps_stripper=None, xmp_stripper=None):
        self.path_guard = path_guard
        self.audit_logger = audit_logger
        self.count = count or getattr(config, 'YEARLY_BEST_COUNT', 12)
        self.gps_stripper = gps_stripper
        self.xmp_stripper = xmp_stripper

    def collect(self, destination: str) -> Dict[int, List[str]]:
        """
        Scansiona HIGHLIGHTS/, raggruppa per anno, copia le migliori N in
        MIGLIORI_ANNO/{anno}_best_{N}/.
        Ritorna {anno: [lista_path_copiate]}.
        """
        highlights_path = os.path.join(
            destination, config.HIGHLIGHTS_FOLDER_NAME
        )
        yearly_folder = self.path_guard.safe_join(
            destination, config.YEARLY_BEST_FOLDER_NAME
        )
        os.makedirs(yearly_folder, exist_ok=True)

        if not os.path.isdir(highlights_path):
            logger.debug("YearlyBest: cartella HIGHLIGHTS non trovata: %s", highlights_path)
            return {}

        # Raccoglie tutte le foto negli HIGHLIGHTS
        all_photos = self._scan_highlights(highlights_path)

        if not all_photos:
            return {}

        # Raggruppa per anno
        by_year = defaultdict(list)
        for photo_info in all_photos:
            year = photo_info['year']
            by_year[year].append(photo_info)

        result = {}

        for year, photos in sorted(by_year.items()):
            # Ordina per quality_score desc, poi per data asc
            photos.sort(key=lambda x: (-x['quality_score'], x['date']))

            # Prendi le prime N
            top_photos = photos[:self.count]

            year_folder_name = f"{year}_best_{self.count}"
            year_folder = self.path_guard.safe_join(yearly_folder, year_folder_name)
            os.makedirs(year_folder, exist_ok=True)

            copied = []
            for photo_info in top_photos:
                src = photo_info['path']
                filename = os.path.basename(src)
                dest = self.path_guard.safe_join(year_folder, filename)

                # Salta se già presente (idempotente)
                if os.path.exists(dest):
                    copied.append(dest)
                    continue

                # AuditLogger PRIMA della copia
                self.audit_logger.log_copy(src, dest)

                # GPS + XMP stripping obbligatorio prima di copiare
                stripped = False
                if self.gps_stripper is not None:
                    try:
                        stripped = self.gps_stripper.strip_gps(src, dest)
                    except Exception as e:
                        logger.debug("GPS strip error: %s", e)

                if not stripped:
                    # XMP stripper come secondo tentativo
                    if self.xmp_stripper is not None:
                        try:
                            self.xmp_stripper.strip_xmp(src, dest)
                        except Exception as e:
                            logger.debug("XMP strip error: %s", e)
                            shutil.copy2(src, dest)
                    else:
                        shutil.copy2(src, dest)

                copied.append(dest)

            result[year] = copied
            logger.debug("YearlyBest %d: %d foto copiate in %s",
                         year, len(copied), year_folder)

        return result

    def _scan_highlights(self, highlights_path: str) -> List[Dict]:
        """Scansiona ricorsivamente gli HIGHLIGHTS e raccoglie info sulle foto."""
        photos = []
        photo_exts = config.PHOTO_EXTENSIONS

        for root, dirs, files in os.walk(highlights_path):
            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext not in photo_exts:
                    continue

                file_path = os.path.join(root, filename)

                # Estrai anno dalla data nel nome file o mtime
                year, date = self._extract_year_date(filename, file_path)

                # quality_score approssimato dalla dimensione file
                try:
                    size = os.path.getsize(file_path)
                    quality_score = min(1.0, size / 3_000_000)  # 3MB = max score
                except Exception:
                    quality_score = 0.5

                photos.append({
                    'path': file_path,
                    'year': year,
                    'date': date,
                    'quality_score': quality_score,
                })

        return photos

    def _extract_year_date(self, filename: str, file_path: str):
        """Estrae anno e data dal nome file o dalla data di modifica."""
        patterns = [
            r'(\d{4})(\d{2})(\d{2})',
            r'(\d{4})[_-](\d{2})[_-](\d{2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                        return y, datetime(y, m, d)
                except (ValueError, IndexError):
                    pass

        # Fallback: data di modifica
        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            return dt.year, dt
        except Exception:
            return datetime.now().year, datetime.now()
