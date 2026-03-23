"""
DecompressionBombGuardAgent — Fase 2, step 1
Configura Pillow per bloccare immagini troppo grandi (decompression bomb).
Da chiamare UNA SOLA VOLTA all'avvio, prima di qualsiasi Image.open().
"""
import warnings
import logging

from PIL import Image

logger = logging.getLogger(__name__)


class DecompressionBombGuardAgent:
    """
    Configura Pillow per bloccare (non solo avvisare) in caso di immagini
    troppo grandi. Da chiamare UNA SOLA VOLTA all'avvio, prima di qualsiasi
    Image.open().
    """

    MAX_PIXELS = 100_000_000  # 100 MP — limite ragionevole per foto da smartphone

    def __init__(self, max_pixels: int = MAX_PIXELS):
        self.max_pixels = max_pixels

    def configure(self):
        """
        Imposta il limite e converte il warning in errore bloccante.
        Chiama questo metodo come prima cosa in main.py.
        """
        Image.MAX_IMAGE_PIXELS = self.max_pixels
        warnings.filterwarnings(
            'error',
            category=Image.DecompressionBombWarning
        )
        logger.debug("DecompressionBombGuard configurato: MAX_IMAGE_PIXELS=%d", self.max_pixels)

    def safe_open(self, file_path: str):
        """
        Apre un'immagine in modo sicuro.
        Ritorna None se è una decompression bomb o se il file è corrotto.
        Deve essere usato SEMPRE al posto di Image.open() diretto.
        """
        try:
            img = Image.open(file_path)
            img.verify()  # Verifica integrità senza caricare i pixel
            # Riapri dopo verify() — verify() consuma il file pointer
            return Image.open(file_path)
        except Image.DecompressionBombWarning:
            logger.warning("DecompressionBombWarning su file: %s", file_path)
            return None
        except Image.DecompressionBombError:
            logger.warning("DecompressionBombError su file: %s", file_path)
            return None
        except Exception as e:
            logger.debug("Errore apertura immagine %s: %s", file_path, e)
            return None
