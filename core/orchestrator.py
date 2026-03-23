"""
Orchestratore centrale — Fase 3, step 21
Coordina la pipeline completa con dependency injection.
AnomalyDetector iniettato in PathGuard per rilevare path traversal.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class PhotoMetadata:
    """Oggetto centrale che viene arricchito da ogni agente del Layer 2."""
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
    quality_score: float = 0.0         # 0.0–1.0, usato da HighlightsCurator
    exif_data: dict = field(default_factory=dict)
    gps: Optional[dict] = None


class Orchestrator:
    """
    Orchestratore centrale con dependency injection.
    Coordina il flusso: Security Gate → Analisi → Elaborazione → Output.
    """

    def __init__(
        self,
        file_validator,
        exif_sanitizer,
        path_guard,
        audit_logger,
        scanner,
        date_analyzer,
        duplicate_detector,
        smart_classifier,
        event_matcher,
        folder_manager,
        highlights_curator,
        yearly_best_collector,
        checkpoint_manager,
        report_generator,
        anomaly_detector=None,
        memory_manager=None,
    ):
        self.file_validator = file_validator
        self.exif_sanitizer = exif_sanitizer
        self.path_guard = path_guard
        self.audit_logger = audit_logger
        self.scanner = scanner
        self.date_analyzer = date_analyzer
        self.duplicate_detector = duplicate_detector
        self.smart_classifier = smart_classifier
        self.event_matcher = event_matcher
        self.folder_manager = folder_manager
        self.highlights_curator = highlights_curator
        self.yearly_best_collector = yearly_best_collector
        self.checkpoint_manager = checkpoint_manager
        self.report_generator = report_generator
        self.anomaly_detector = anomaly_detector
        self.memory_manager = memory_manager

        # Inietta AnomalyDetector in PathGuard per rilevare traversal
        if self.anomaly_detector is not None:
            self._inject_anomaly_detector_into_path_guard()

    def _inject_anomaly_detector_into_path_guard(self):
        """Wrappa safe_join per rilevare tentativi di path traversal."""
        original_safe_join = self.path_guard.safe_join

        def monitored_safe_join(base, *parts):
            try:
                return original_safe_join(base, *parts)
            except ValueError as e:
                err_str = str(e)
                if 'traversal' in err_str.lower() or 'fuori dalla sandbox' in err_str.lower():
                    attempted = '/'.join(str(p) for p in parts)
                    self.anomaly_detector.on_traversal_attempt(attempted)
                    self.audit_logger.log_event(
                        'PATH_TRAVERSAL_BLOCKED',
                        attempted[:100]
                    )
                raise

        self.path_guard.safe_join = monitored_safe_join

    def run(self, source_folder: str, destination_folder: str) -> dict:
        """
        Esegue la pipeline completa.
        Ritorna un dizionario di statistiche.
        """
        stats = {
            'total': 0,
            'moved': 0,
            'duplicates': 0,
            'errors': 0,
            'highlights': 0,
            'yearly_best': {},
        }

        # 1. Assicura che la destination sia nella sandbox
        self.path_guard.add_allowed_root(destination_folder)

        # 2. Scansione
        all_files = self.scanner.scan(source_folder)
        stats['total'] = len(all_files)
        logger.debug("Scansione: trovati %d file", stats['total'])

        # 3. Carica checkpoint (file già processati)
        processed = set(self.checkpoint_manager.load())

        for file_path in all_files:
            if file_path in processed:
                logger.debug("Saltato (già processato): %s", file_path)
                continue

            try:
                # ── LAYER 1: Security Gate ─────────────────────────────
                if not self.file_validator.validate(file_path):
                    errors = self.file_validator.get_errors()
                    self.audit_logger.log_skip(file_path, errors)
                    stats['errors'] += 1
                    continue

                exif = self.exif_sanitizer.sanitize(file_path)

                # ── LAYER 2: Analisi ───────────────────────────────────
                meta = PhotoMetadata(original_path=file_path, current_path=file_path)
                meta.exif_data = exif
                meta.gps = exif.get('gps')

                meta = self.date_analyzer.analyze(meta, exif)
                meta = self.duplicate_detector.check(meta)
                meta = self.smart_classifier.classify(meta)

                if meta.is_duplicate:
                    self.audit_logger.log_skip(file_path, f'duplicato di {meta.duplicate_of}')
                    stats['duplicates'] += 1
                    continue

                # ── LAYER 3: Elaborazione ──────────────────────────────
                meta = self.event_matcher.match(meta)
                new_path = self.folder_manager.organize(meta, destination_folder)
                self.audit_logger.log_move(file_path, new_path)
                meta.current_path = new_path
                stats['moved'] += 1

                # Highlights automatici
                if self.highlights_curator.should_promote(meta):
                    meta = self.highlights_curator.promote(
                        meta, meta.event_name or 'Auto', self.folder_manager
                    )
                    if meta.is_highlight:
                        stats['highlights'] += 1

                # ── LAYER 4: Checkpoint ────────────────────────────────
                self.checkpoint_manager.save(meta)

            except Exception as e:
                logger.error("Errore processando %s: %s", file_path, e)
                self.audit_logger.log_skip(file_path, f'errore: {e}')
                stats['errors'] += 1

        # ── Raccolta annuale highlights ────────────────────────────────
        try:
            yearly_result = self.yearly_best_collector.collect(destination_folder)
            stats['yearly_best'] = yearly_result
        except Exception as e:
            logger.error("YearlyBestCollector errore: %s", e)

        # ── Report finale ──────────────────────────────────────────────
        try:
            self.report_generator.generate(stats, destination_folder)
        except Exception as e:
            logger.error("ReportGenerator errore: %s", e)

        logger.debug("Pipeline completata: %s", stats)
        return stats
