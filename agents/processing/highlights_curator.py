"""
HighlightsCuratorAgent — Fase 4, step 28
Decide se promuovere automaticamente una foto agli highlights in base
alla quality_score o a flag espliciti dell'utente.
"""
import logging

logger = logging.getLogger(__name__)


class HighlightsCuratorAgent:
    """
    Decide se una foto merita di essere promossa agli HIGHLIGHTS.

    Criteri di promozione automatica:
    - meta.quality_score >= quality_threshold
    - Oppure: foto già contrassegnata dall'utente (meta.is_highlight = True)
    """

    def __init__(self, quality_threshold: float = 0.7):
        self.quality_threshold = quality_threshold

    def should_promote(self, meta) -> bool:
        """
        Ritorna True se la foto deve essere promossa agli highlights.
        """
        if meta.is_highlight:
            return True
        return meta.quality_score >= self.quality_threshold

    def promote(self, meta, highlight_name: str, folder_manager) -> object:
        """
        Promuove la foto all'highlight specificato.
        Ritorna meta aggiornato con is_highlight=True e highlight_name.
        """
        try:
            new_path = folder_manager.move_to_highlight(meta, highlight_name)
            meta.is_highlight = True
            meta.highlight_name = highlight_name
            logger.debug("Foto promossa a highlight '%s': %s", highlight_name, meta.current_path)
        except Exception as e:
            logger.debug("HighlightsCurator: impossibile promuovere %s: %s",
                         meta.current_path, e)
        return meta
