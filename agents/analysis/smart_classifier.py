"""
SmartClassifierAgent — Fase 3, step 25
Classifica le foto con tag e quality_score.
Modalità AI (CLIP/transformers) opzionale, con fallback robusto.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# AI opzionale — fallback graceful se non disponibile
try:
    from transformers import pipeline
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.debug("transformers non disponibile: uso fallback classifier")


class SmartClassifierAgent:
    """
    Classifica le foto generando tag e quality_score.

    Modalità AI (use_ai=True, librerie disponibili):
      - Usa CLIP/transformers per tag semantici
      - quality_score reale

    Modalità fallback (predefinita):
      - Inferisce tag dal nome file e cartella sorgente
      - quality_score basato su dimensione file (proxy per qualità)
    """

    def __init__(self, use_ai: bool = False):
        self.use_ai = use_ai and AI_AVAILABLE
        self._ai_pipeline = None

        if self.use_ai:
            try:
                self._ai_pipeline = pipeline(
                    "zero-shot-image-classification",
                    model="openai/clip-vit-base-patch32"
                )
            except Exception as e:
                logger.warning("Impossibile caricare CLIP: %s — uso fallback", e)
                self.use_ai = False

    def classify(self, meta):
        """
        Classifica la foto. Imposta meta.tags e meta.quality_score.
        Non lancia mai eccezioni.
        Ritorna meta aggiornato.
        """
        try:
            if self.use_ai and self._ai_pipeline:
                return self._classify_ai(meta)
            else:
                return self._classify_fallback(meta)
        except Exception as e:
            logger.debug("SmartClassifier error su %s: %s", meta.current_path, e)
            meta.tags = []
            meta.quality_score = 0.5
            return meta

    def _classify_ai(self, meta):
        """Classificazione con CLIP."""
        candidate_labels = [
            'spiaggia', 'montagna', 'città', 'natura', 'persone',
            'cibo', 'tramonto', 'festa', 'viaggio', 'sport'
        ]
        try:
            result = self._ai_pipeline(meta.current_path, candidate_labels)
            meta.tags = [r['label'] for r in result[:3] if r['score'] > 0.2]
            meta.quality_score = result[0]['score'] if result else 0.5
        except Exception as e:
            logger.debug("CLIP error: %s", e)
            return self._classify_fallback(meta)
        return meta

    def _classify_fallback(self, meta):
        """Classificazione senza AI: usa nome file, cartella, dimensione."""
        filename = Path(meta.current_path).stem.lower()
        parent = Path(meta.current_path).parent.name.lower()

        tags = []

        # Tag da parole chiave nel nome file/cartella
        keywords = {
            'spiaggia': ['beach', 'mare', 'spiaggia', 'sea', 'ocean'],
            'montagna': ['mountain', 'montagna', 'alpi', 'neve', 'snow', 'ski'],
            'festa': ['party', 'festa', 'compleanno', 'birthday', 'natale', 'christmas'],
            'viaggio': ['travel', 'viaggio', 'trip', 'tour', 'vacation', 'vacanza'],
            'estate': ['estate', 'summer', 'luglio', 'agosto'],
            'inverno': ['inverno', 'winter', 'dicembre', 'gennaio'],
        }

        combined = filename + ' ' + parent
        for tag, kws in keywords.items():
            if any(kw in combined for kw in kws):
                tags.append(tag)

        meta.tags = tags[:5]  # Massimo 5 tag

        # quality_score basato su dimensione file (proxy per qualità)
        try:
            size_bytes = os.path.getsize(meta.current_path)
            # > 2MB = alta qualità, < 100KB = bassa qualità
            if size_bytes > 2_000_000:
                meta.quality_score = 0.8
            elif size_bytes > 500_000:
                meta.quality_score = 0.6
            elif size_bytes > 100_000:
                meta.quality_score = 0.4
            else:
                meta.quality_score = 0.2
        except Exception:
            meta.quality_score = 0.5

        return meta
