"""
ScannerAgent — Fase 3, step 22
Scansiona una cartella sorgente e restituisce la lista ordinata di file foto.
"""
import os
import logging
from pathlib import Path
from typing import List, Set

import config

logger = logging.getLogger(__name__)


class ScannerAgent:
    """
    Scansiona una cartella sorgente e ritorna la lista di file foto.
    Ricicla la logica di utils/file_utils.py:load_all_photos().
    """

    def __init__(self, extensions: Set[str] = None):
        if extensions is None:
            self.extensions = config.PHOTO_EXTENSIONS
        else:
            self.extensions = {ext.lower() for ext in extensions}

    def scan(self, folder: str) -> List[str]:
        """
        Scansiona ricorsivamente la cartella e ritorna lista di path ordinata.
        """
        if not folder or not os.path.isdir(folder):
            logger.warning("ScannerAgent: cartella non trovata: %s", folder)
            return []

        photos = []
        for root, dirs, files in os.walk(folder):
            for filename in files:
                file_path = os.path.join(root, filename)
                ext = Path(filename).suffix.lower()
                if ext in self.extensions:
                    photos.append(file_path)

        photos.sort()
        logger.debug("Scanner: trovate %d foto in %s", len(photos), folder)
        return photos
