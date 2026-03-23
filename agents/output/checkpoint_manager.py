"""
CheckpointManagerAgent — Fase 5, step 30
Gestisce il file di checkpoint validando ogni path con PathGuard.
"""
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class CheckpointManagerAgent:
    """
    Gestisce il salvataggio e il caricamento del checkpoint di progressi.
    Valida ogni percorso letto con PathGuardAgent.is_safe_path().
    Compatibile con il formato originale di progress_checkpoint.txt.
    """

    def __init__(self, checkpoint_path: str, path_guard):
        self.checkpoint_path = checkpoint_path
        self.path_guard = path_guard
        self._processed: set = set()

    def save(self, meta) -> None:
        """Salva il path corrente nel checkpoint."""
        self._processed.add(meta.current_path)
        try:
            with open(self.checkpoint_path, 'a', encoding='utf-8') as f:
                f.write(meta.current_path + '\n')
        except Exception as e:
            logger.debug("Checkpoint save error: %s", e)

    def load(self) -> List[str]:
        """
        Carica i path già processati dal checkpoint.
        Ogni path viene validato con PathGuard — quelli non validi vengono ignorati.
        """
        if not os.path.exists(self.checkpoint_path):
            return []

        valid_paths = []
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                for line in f:
                    path = line.strip()
                    if not path:
                        continue
                    # Valida con PathGuard prima di usare
                    if self.path_guard.is_safe_path(path):
                        valid_paths.append(path)
                    else:
                        logger.warning(
                            "Checkpoint: path non sicuro ignorato: %s",
                            os.path.basename(path)
                        )
        except Exception as e:
            logger.debug("Checkpoint load error: %s", e)

        return valid_paths

    def clear(self) -> None:
        """Azzera il checkpoint."""
        self._processed.clear()
        if os.path.exists(self.checkpoint_path):
            try:
                os.remove(self.checkpoint_path)
            except Exception as e:
                logger.debug("Checkpoint clear error: %s", e)

    def exists(self) -> bool:
        """Ritorna True se esiste un checkpoint."""
        return os.path.exists(self.checkpoint_path)
