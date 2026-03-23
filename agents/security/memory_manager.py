"""
MemoryManagerAgent — Fase 2, step 2
Gestisce apertura sicura di immagini PIL prevenendo memory leak.
Forza garbage collection periodica su archivi grandi.
"""
import gc
import contextlib
import logging
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class MemoryManagerAgent:
    """
    Gestisce apertura sicura di immagini PIL prevenendo memory leak.
    Forza garbage collection periodica su archivi grandi.

    Documentato in Pillow issue #7935 (2024): ogni immagine processata lascia
    ~8MB di memoria non rilasciata. Con 350 foto questo causa crash su 8GB RAM.
    """

    def __init__(self, gc_every_n_photos: int = 50):
        self.gc_every_n_photos = gc_every_n_photos
        self._photo_count = 0

    @contextlib.contextmanager
    def open_image(self, file_path: str):
        """
        Context manager sicuro per aprire immagini.
        Garantisce la chiusura anche in caso di eccezioni.

        Uso:
            with memory_manager.open_image(path) as img:
                thumbnail = img.copy()
        """
        img = None
        try:
            img = Image.open(file_path)
            img.load()  # Forza il caricamento in memoria ora
            yield img
        finally:
            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
            self._photo_count += 1
            if self._photo_count % self.gc_every_n_photos == 0:
                gc.collect()
                logger.debug("GC forzato dopo %d foto", self._photo_count)

    def open_thumbnail(self, file_path: str,
                       max_size: Tuple[int, int] = (800, 600)) -> Optional[Image.Image]:
        """
        Apre un'immagine, ne crea una thumbnail e chiude l'originale.
        Ritorna la thumbnail (in memoria, piccola) o None.
        Tutti i Image.open() nella GUI devono passare per questo metodo.
        """
        try:
            with self.open_image(file_path) as img:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                return img.copy()  # Copia prima che il context manager chiuda
        except Exception as e:
            logger.debug("Errore apertura thumbnail %s: %s", file_path, e)
            return None

    def force_gc(self):
        """Forza garbage collection manuale."""
        gc.collect()
        logger.debug("GC manuale forzato")
