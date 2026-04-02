"""
Orchestratore centrale — versione essenziale
Coordina la pipeline: Validazione → Analisi data → Organizzazione cartelle.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class PhotoMetadata:
    """Oggetto centrale arricchito dagli agenti della pipeline."""
    original_path: str
    current_path: str
    date: Optional[datetime] = None
    date_source: str = 'unknown'       # 'exif', 'filename', 'mtime'
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    event_name: Optional[str] = None
    event_priority: int = 0
    is_highlight: bool = False
    highlight_name: Optional[str] = None
    quality_score: float = 0.0
    exif_data: dict = field(default_factory=dict)
    gps: Optional[dict] = None


class Orchestrator:
    """
    Orchestratore con dependency injection.
    Pipeline: file_validator → date_analyzer → folder_manager.
    """

    def __init__(
        self,
        file_validator,
        path_guard,
        audit_logger,
        scanner,
        date_analyzer,
        folder_manager,
    ):
        self.file_validator = file_validator
        self.path_guard = path_guard
        self.audit_logger = audit_logger
        self.scanner = scanner
        self.date_analyzer = date_analyzer
        self.folder_manager = folder_manager

    def run(self, source_folder: str, destination_folder: str) -> dict:
        """
        Esegue la pipeline completa.
        Ritorna un dizionario di statistiche.
        """
        stats = {
            'total': 0,
            'moved': 0,
            'errors': 0,
        }

        self.path_guard.add_allowed_root(destination_folder)

        all_files = self.scanner.scan(source_folder)
        stats['total'] = len(all_files)
        logger.debug("Scansione: trovati %d file", stats['total'])

        for file_path in all_files:
            try:
                # Validazione
                if not self.file_validator.validate(file_path):
                    errors = self.file_validator.get_errors()
                    self.audit_logger.log_skip(file_path, errors)
                    stats['errors'] += 1
                    continue

                # Analisi
                meta = PhotoMetadata(original_path=file_path, current_path=file_path)
                meta = self.date_analyzer.analyze(meta, {})

                # Organizzazione
                new_path = self.folder_manager.organize(meta, destination_folder)
                self.audit_logger.log_move(file_path, new_path)
                meta.current_path = new_path
                stats['moved'] += 1

            except Exception as e:
                logger.error("Errore processando %s: %s", file_path, e)
                self.audit_logger.log_skip(file_path, f'errore: {e}')
                stats['errors'] += 1

        logger.debug("Pipeline completata: %s", stats)
        return stats
