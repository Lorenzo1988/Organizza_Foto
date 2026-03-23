"""
DuplicateDetectorAgent — Fase 3, step 24
Rileva duplicati tramite MD5 esatto e pHash perceptual (se imagehash disponibile).
"""
import hashlib
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import imagehash
    from PIL import Image
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.debug("imagehash non disponibile: solo rilevamento MD5")


class DuplicateDetectorAgent:
    """
    Rileva duplicati con due strategie:
    1. MD5 dell'intero file → match esatto
    2. pHash (perceptual hash) → match visivo (immagini quasi identiche)

    Mantiene un dizionario interno {hash: path} tra le chiamate.
    """

    def __init__(self, hash_threshold: int = 8):
        self.hash_threshold = hash_threshold
        self._md5_cache: Dict[str, str] = {}     # {md5: original_path}
        self._phash_cache: Dict[str, str] = {}    # {phash_str: original_path}

    def check(self, meta):
        """
        Verifica se la foto è duplicata.
        Imposta meta.is_duplicate e meta.duplicate_of se trovato.
        Ritorna meta aggiornato.
        """
        file_path = meta.current_path

        # 1. MD5 esatto
        md5 = self._compute_md5(file_path)
        if md5:
            if md5 in self._md5_cache:
                meta.is_duplicate = True
                meta.duplicate_of = self._md5_cache[md5]
                logger.debug("Duplicato MD5: %s == %s", file_path, meta.duplicate_of)
                return meta
            self._md5_cache[md5] = file_path

        # 2. pHash visivo (solo se imagehash disponibile)
        if IMAGEHASH_AVAILABLE:
            phash = self._compute_phash(file_path)
            if phash is not None:
                # Cerca match visivo
                for stored_hash_str, stored_path in self._phash_cache.items():
                    try:
                        stored_hash = imagehash.hex_to_hash(stored_hash_str)
                        distance = phash - stored_hash
                        if distance <= self.hash_threshold:
                            meta.is_duplicate = True
                            meta.duplicate_of = stored_path
                            logger.debug(
                                "Duplicato pHash (dist=%d): %s == %s",
                                distance, file_path, stored_path
                            )
                            return meta
                    except Exception:
                        continue
                self._phash_cache[str(phash)] = file_path

        return meta

    def clear_cache(self):
        """Svuota la cache dei hash (utile per test o batch multipli)."""
        self._md5_cache.clear()
        self._phash_cache.clear()

    def _compute_md5(self, file_path: str) -> Optional[str]:
        """Calcola MD5 dell'intero file."""
        try:
            h = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            logger.debug("MD5 error su %s: %s", file_path, e)
            return None

    def _compute_phash(self, file_path: str) -> Optional[object]:
        """Calcola perceptual hash dell'immagine."""
        try:
            with Image.open(file_path) as img:
                return imagehash.phash(img)
        except Exception as e:
            logger.debug("pHash error su %s: %s", file_path, e)
            return None
