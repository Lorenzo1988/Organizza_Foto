"""
FileValidatorAgent — Fase 2, step 3
Valida i file immagine tramite magic bytes, dimensione ed estensione.
Mitiga il file masquerading (file EXE rinominati .jpg, ecc.).
"""
import os
import logging
from pathlib import Path
from typing import List

from config import PHOTO_EXTENSIONS

logger = logging.getLogger(__name__)

# Magic bytes delle immagini supportate
MAGIC_SIGNATURES = {
    b'\xff\xd8\xff': 'JPEG',
    b'\x89PNG': 'PNG',
    b'GIF87a': 'GIF',
    b'GIF89a': 'GIF',
    b'BM': 'BMP',
    b'II*\x00': 'TIFF',
    b'MM\x00*': 'TIFF',
    b'\x00\x00\x00\x0cftyp': 'HEIC',
    b'ftypheic': 'HEIC',
    b'ftypmif1': 'HEIC',
    b'ftypmsf1': 'HEIC',
    b'ftypHEIC': 'HEIC',
    b'ftypMIF1': 'HEIC',
}


class FileValidatorAgent:
    """
    Valida i file immagine controllando:
    1. Esistenza del file
    2. Estensione nella whitelist
    3. Dimensione > 0 e < max_size_mb
    4. Magic bytes corrispondenti al tipo dichiarato

    Non lancia mai eccezioni: ritorna True o False.
    """

    def __init__(self, max_size_mb: int = 200):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._errors: List[str] = []

    def validate(self, file_path: str) -> bool:
        """
        Valida un file immagine. Ritorna True se valido, False altrimenti.
        Popola get_errors() con i dettagli del fallimento.
        """
        self._errors = []

        # 1. Esistenza
        if not os.path.isfile(file_path):
            self._errors.append(f"File non trovato: {file_path}")
            return False

        # 2. Estensione nella whitelist
        ext = Path(file_path).suffix.lower()
        if ext not in PHOTO_EXTENSIONS:
            self._errors.append(f"Estensione non supportata: {ext}")
            return False

        # 3. Dimensione
        try:
            size = os.path.getsize(file_path)
        except OSError as e:
            self._errors.append(f"Impossibile leggere dimensione: {e}")
            return False

        if size == 0:
            self._errors.append("File vuoto (0 byte)")
            return False

        if size > self.max_size_bytes:
            self._errors.append(
                f"File troppo grande: {size // (1024*1024)}MB > {self.max_size_bytes // (1024*1024)}MB"
            )
            return False

        # 4. Magic bytes
        if not self._check_magic_bytes(file_path, ext):
            self._errors.append("Magic bytes non validi (possibile file mascherato)")
            return False

        return True

    def get_errors(self) -> List[str]:
        """Ritorna la lista degli errori dell'ultima chiamata a validate()."""
        return list(self._errors)

    def _check_magic_bytes(self, file_path: str, ext: str) -> bool:
        """Legge i primi 16 byte e verifica la firma del file."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
        except OSError:
            return False

        if len(header) < 2:
            return False

        # Controlla tutte le signature note
        for magic, fmt in MAGIC_SIGNATURES.items():
            if header[:len(magic)] == magic:
                return True

        # HEIC: ftyp box può avere offset variabile
        if ext in {'.heic', '.heif'} and len(header) >= 12:
            # Controlla il brand a byte 4-12
            brand = header[4:12]
            heic_brands = [b'ftypheic', b'ftypmif1', b'ftypmsf1', b'ftypHEIC', b'ftypMIF1']
            for b in heic_brands:
                if b in brand:
                    return True

        return False
