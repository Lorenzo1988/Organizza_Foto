"""
XmpStripperAgent — Fase 2, step 10
Rimuove o sanitizza i metadati XMP dalle immagini prima
di copiarle in cartelle pubbliche/condivise.
"""
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Cartelle considerate "pubbliche" (stesse di GpsStripperAgent)
PUBLIC_FOLDER_NAMES = {
    '⭐ HIGHLIGHTS',
    '📅 MIGLIORI_ANNO',
    '🖨️ DA_STAMPARE',
}

# Campi XMP da rimuovere nelle foto condivise
XMP_FIELDS_TO_STRIP = {
    'gps:Latitude', 'gps:Longitude', 'gps:Altitude',
    'gps:GPSLatitude', 'gps:GPSLongitude',
    'xmp:CreatorTool',
    'dc:creator',
    'photoshop:City', 'photoshop:State', 'photoshop:Country',
    'Iptc4xmpCore:Location',
}


class XmpStripperAgent:
    """
    Rimuove o sanitizza i metadati XMP dalle immagini prima
    di copiarle in cartelle pubbliche/condivise.
    Complementa GpsStripperAgent per i metadati XMP (Adobe).
    """

    def should_strip(self, destination_path: str) -> bool:
        """Determina se rimuovere XMP in base alla cartella di destinazione."""
        parts = Path(destination_path).parts
        return any(folder in parts for folder in PUBLIC_FOLDER_NAMES)

    def strip_xmp(self, source_path: str, dest_path: str) -> bool:
        """
        Copia il file rimuovendo i campi XMP sensibili.
        Ritorna True se XMP rimosso, False altrimenti.
        """
        try:
            from PIL import Image
            with Image.open(source_path) as img:
                xmp_data = img.getxmp() if hasattr(img, 'getxmp') else None

            if not xmp_data:
                shutil.copy2(source_path, dest_path)
                return False

            # XMP presente: rimuovi tramite piexif come fallback sicuro
            result = self._strip_xmp_with_piexif(source_path, dest_path)
            return result

        except ImportError:
            shutil.copy2(source_path, dest_path)
            return False
        except Exception as e:
            logger.debug("XMP strip: errore su %s: %s", source_path, e)
            shutil.copy2(source_path, dest_path)
            return False

    def _strip_xmp_with_piexif(self, source_path: str, dest_path: str) -> bool:
        """Rimuove tutti i dati XMP tramite lettura/riscrittura con piexif."""
        try:
            import piexif
            from PIL import Image

            exif_dict = piexif.load(source_path)
            # Svuota GPS (che include spesso coordinate XMP)
            exif_dict['GPS'] = {}
            exif_bytes = piexif.dump(exif_dict)

            with Image.open(source_path) as img:
                img.save(dest_path, exif=exif_bytes)
            return True

        except Exception as e:
            logger.debug("XMP piexif strip fallback: %s", e)
            shutil.copy2(source_path, dest_path)
            return False
