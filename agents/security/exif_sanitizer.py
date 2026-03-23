"""
ExifSanitizerAgent — Fase 2, step 4
Legge e sanitizza i metadati EXIF usando getexif() (NON _getexif()).
Usa una whitelist di tag e valida i valori.
"""
import logging
import string
from datetime import datetime
from typing import Dict, Any, Optional

from PIL import Image
from PIL.ExifTags import TAGS

logger = logging.getLogger(__name__)

# Tag EXIF consentiti (whitelist)
ALLOWED_TAG_NAMES = {
    'DateTimeOriginal', 'DateTime', 'DateTimeDigitized',
    'GPSInfo', 'Make', 'Model', 'Orientation',
    'ImageWidth', 'ImageLength', 'ExifImageWidth', 'ExifImageHeight',
}

# IFD tag per GPS e EXIF sub-IFD
GPS_IFD_TAG = 0x8825
EXIF_IFD_TAG = 0x8769

# Nomi dei tag GPS
GPS_TAG_NAMES = {
    1: 'GPSLatitudeRef', 2: 'GPSLatitude',
    3: 'GPSLongitudeRef', 4: 'GPSLongitude',
    5: 'GPSAltitudeRef', 6: 'GPSAltitude',
}

MAX_STRING_LENGTH = 256
PRINTABLE = set(string.printable)


class ExifSanitizerAgent:
    """
    Legge i metadati EXIF da un file immagine usando l'API pubblica
    getexif() (mai _getexif()). Sanitizza i valori con una whitelist.

    Ritorna sempre un dizionario strutturato, mai None.
    Non lancia mai eccezioni.
    """

    def sanitize(self, file_path: str) -> Dict[str, Any]:
        """
        Legge e sanitizza i metadati EXIF.

        Ritorna:
            {
                'date': datetime | None,
                'source': 'exif' | 'none',
                'gps': {'lat': float, 'lon': float} | None,
                'make': str | None,
                'model': str | None,
                'orientation': int,  # 1-8
            }
        """
        result = {
            'date': None,
            'source': 'none',
            'gps': None,
            'make': None,
            'model': None,
            'orientation': 1,
        }

        try:
            with Image.open(file_path) as img:
                # API pubblica stabile da Pillow 6.0 — NON _getexif()
                exif_data = img.getexif()
                if not exif_data:
                    return result

                # Leggi i tag principali
                for tag_id, raw_value in exif_data.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    if tag_name not in ALLOWED_TAG_NAMES:
                        continue
                    sanitized = self._sanitize_value(raw_value)
                    if sanitized is None:
                        continue
                    self._assign_field(result, tag_name, sanitized)

                # GPS IFD — letto tramite get_ifd (NON dal dizionario principale)
                gps_ifd = exif_data.get_ifd(GPS_IFD_TAG)
                if gps_ifd:
                    result['gps'] = self._parse_gps(gps_ifd)

        except Exception as e:
            logger.debug("Errore lettura EXIF da %s: %s", file_path, e)

        return result

    # ── Interni ───────────────────────────────────────────────────

    def _assign_field(self, result: dict, tag_name: str, value: Any):
        """Assegna un valore sanitizzato al campo corretto del result."""
        if tag_name in ('DateTimeOriginal', 'DateTime', 'DateTimeDigitized'):
            if result['date'] is None:  # Prima data trovata vince
                dt = self._parse_datetime(value)
                if dt:
                    result['date'] = dt
                    result['source'] = 'exif'
        elif tag_name == 'Make':
            result['make'] = value if isinstance(value, str) else None
        elif tag_name == 'Model':
            result['model'] = value if isinstance(value, str) else None
        elif tag_name == 'Orientation':
            if isinstance(value, int) and 1 <= value <= 8:
                result['orientation'] = value

    def _sanitize_value(self, value: Any) -> Any:
        """
        Sanitizza un valore EXIF. Accetta solo tipi primitivi sicuri.
        Ritorna None se il valore non è accettabile.
        """
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return value
        if isinstance(value, str):
            # Solo caratteri stampabili, lunghezza massima
            sanitized = ''.join(c for c in value if c in PRINTABLE)
            return sanitized[:MAX_STRING_LENGTH] if sanitized else None
        if isinstance(value, (tuple, list)):
            sanitized = []
            for item in value:
                if isinstance(item, (int, float)):
                    sanitized.append(item)
                elif hasattr(item, 'numerator') and hasattr(item, 'denominator'):
                    # IFDRational
                    if item.denominator != 0:
                        sanitized.append(float(item))
            return tuple(sanitized) if sanitized else None
        # Ignora bytes, dict e altri tipi complessi
        return None

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        """Parsa una stringa data EXIF in formato YYYY:MM:DD HH:MM:SS."""
        if not isinstance(value, str):
            return None
        try:
            return datetime.strptime(value.strip(), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            try:
                return datetime.strptime(value.strip()[:10], "%Y:%m:%d")
            except ValueError:
                return None

    def _parse_gps(self, gps_ifd: dict) -> Optional[Dict[str, float]]:
        """Parsa il GPS IFD e ritorna lat/lon come float, o None."""
        try:
            lat_ref = gps_ifd.get(1)  # GPSLatitudeRef ('N' o 'S')
            lat = gps_ifd.get(2)      # GPSLatitude (tuple di IFDRational)
            lon_ref = gps_ifd.get(3)  # GPSLongitudeRef ('E' o 'W')
            lon = gps_ifd.get(4)      # GPSLongitude

            if not all([lat_ref, lat, lon_ref, lon]):
                return None

            lat_deg = self._dms_to_decimal(lat, lat_ref)
            lon_deg = self._dms_to_decimal(lon, lon_ref)

            if lat_deg is None or lon_deg is None:
                return None

            return {'lat': lat_deg, 'lon': lon_deg}
        except Exception:
            return None

    def _dms_to_decimal(self, dms, ref: str) -> Optional[float]:
        """Converte gradi/minuti/secondi in gradi decimali."""
        try:
            def to_float(v):
                if isinstance(v, (int, float)):
                    return float(v)
                if hasattr(v, 'numerator') and hasattr(v, 'denominator'):
                    return float(v.numerator) / float(v.denominator) if v.denominator else 0.0
                return float(v)

            d = to_float(dms[0])
            m = to_float(dms[1])
            s = to_float(dms[2])
            decimal = d + m / 60.0 + s / 3600.0

            if isinstance(ref, str) and ref.upper() in ('S', 'W'):
                decimal = -decimal

            return decimal
        except Exception:
            return None
