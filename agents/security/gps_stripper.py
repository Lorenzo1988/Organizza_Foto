"""
GpsStripperAgent — Fase 2, step 9
Rimuove i dati GPS dai metadati EXIF prima di copiare una foto
in cartelle destinate alla condivisione pubblica o al cloud.
"""
import logging
import os
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Cartelle considerate "pubbliche" o a rischio condivisione
PUBLIC_FOLDER_NAMES = {
    '⭐ HIGHLIGHTS',
    '📅 MIGLIORI_ANNO',
    '🖨️ DA_STAMPARE',
}


class GpsStripperAgent:
    """
    Rimuove i dati GPS dai metadati EXIF prima di copiare una foto
    in cartelle destinate alla condivisione pubblica o al cloud.
    """

    def __init__(self, strip_always: bool = False):
        """
        strip_always: se True, rimuove GPS da TUTTE le foto (non solo quelle pubbliche).
        Default False: rimuove solo nelle cartelle a rischio.
        """
        self.strip_always = strip_always

    def should_strip(self, destination_path: str) -> bool:
        """Determina se rimuovere GPS in base alla cartella di destinazione."""
        if self.strip_always:
            return True
        parts = Path(destination_path).parts
        return any(folder in parts for folder in PUBLIC_FOLDER_NAMES)

    def strip_gps(self, source_path: str, dest_path: str) -> bool:
        """
        Copia il file rimuovendo i dati GPS.
        Ritorna True se GPS rimosso, False se non c'era GPS o operazione fallita.
        """
        try:
            import piexif
            exif_dict = piexif.load(source_path)

            had_gps = bool(exif_dict.get('GPS'))
            if 'GPS' in exif_dict:
                exif_dict['GPS'] = {}  # svuota il blocco GPS

            exif_bytes = piexif.dump(exif_dict)

            from PIL import Image
            try:
                with Image.open(source_path) as img:
                    # Salva nella destinazione con EXIF senza GPS
                    img.save(dest_path, exif=exif_bytes)
                return had_gps
            except Exception as e:
                logger.debug("GPS strip: fallback copia normale su %s: %s", source_path, e)
                shutil.copy2(source_path, dest_path)
                return False

        except ImportError:
            logger.debug("piexif non disponibile: copia senza stripping GPS")
            shutil.copy2(source_path, dest_path)
            return False
        except Exception as e:
            logger.debug("GPS strip: errore su %s: %s", source_path, e)
            shutil.copy2(source_path, dest_path)
            return False

    def strip_gps_inplace(self, file_path: str) -> bool:
        """Rimuove GPS dal file in-place (sovrascrive il file originale)."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
                tmp_path = tmp.name
            result = self.strip_gps(file_path, tmp_path)
            if result:
                shutil.move(tmp_path, file_path)
                tmp_path = None
            return result
        except Exception as e:
            logger.debug("GPS strip inplace: errore su %s: %s", file_path, e)
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
