"""
DateAnalyzerAgent — Fase 3, step 23
Estrae la data di scatto da più sorgenti con priorità: EXIF → filename → mtime.
"""
import os
import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Pattern per date nel filename
DATE_PATTERNS = [
    (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),
    (r'(\d{4})[_-](\d{2})[_-](\d{2})', '%Y-%m-%d'),
    (r'(\d{4})\.(\d{2})\.(\d{2})', '%Y.%m.%d'),
]


class DateAnalyzerAgent:
    """
    Estrae la data di scatto con priorità:
    1. exif['date'] (già estratto e sanitizzato da ExifSanitizerAgent)
    2. Data nel filename (pattern YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD)
    3. Data di modifica del file (os.path.getmtime)
    """

    def analyze(self, meta, exif: dict):
        """
        Arricchisce meta.date e meta.date_source.
        Ritorna meta aggiornato.
        """
        # 1. Da EXIF
        if exif.get('date') is not None:
            meta.date = exif['date']
            meta.date_source = 'exif'
            return meta

        # 2. Dal filename
        filename = os.path.basename(meta.current_path)
        date_from_filename = self._extract_from_filename(filename)
        if date_from_filename:
            meta.date = date_from_filename
            meta.date_source = 'filename'
            return meta

        # 3. Dalla data di modifica
        try:
            mtime = os.path.getmtime(meta.current_path)
            meta.date = datetime.fromtimestamp(mtime)
            meta.date_source = 'mtime'
        except Exception as e:
            logger.debug("DateAnalyzer: impossibile leggere mtime di %s: %s",
                         meta.current_path, e)
            meta.date = datetime(2000, 1, 1)
            meta.date_source = 'unknown'

        return meta

    def _extract_from_filename(self, filename: str) -> Optional[datetime]:
        """Cerca una data nel nome del file."""
        for pattern, fmt in DATE_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
        return None
