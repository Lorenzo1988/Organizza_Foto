#!/usr/bin/env python3
"""
Photo Organizer v2 — Multi-Agent Architecture
Entry point con PIL hardening, security gate completo e GUI tkinter.
"""

# ── FASE 1: PIL Hardening (PRIMA DI TUTTO) ────────────────────────────────
import warnings
import os, sys
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = 100_000_000  # 100 MP — decompression bomb protection
warnings.filterwarnings('error', category=Image.DecompressionBombWarning)
ImageFile.LOAD_TRUNCATED_IMAGES = False  # non caricare immagini troncate silenziosamente

# ── Import standard ────────────────────────────────────────────────────────
import logging
import tkinter as tk
from tkinter import messagebox

# Configura logging dal .env
from dotenv import load_dotenv
load_dotenv()

log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.WARNING),
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────
from config import (
    SOURCE_FOLDER, DESTINATION_FOLDER,
    AUDIT_LOG_FILE, YEARLY_BEST_COUNT,
    MAX_PHOTO_SIZE_MB, DUPLICATE_HASH_THRESHOLD,
    PROGRESS_FILE
)

# ── Security Gate ─────────────────────────────────────────────────────────
from agents.security.credential_guard import CredentialGuardAgent
from agents.security.decompression_bomb_guard import DecompressionBombGuardAgent
from agents.security.memory_manager import MemoryManagerAgent
from agents.security.file_validator import FileValidatorAgent
from agents.security.exif_sanitizer import ExifSanitizerAgent
from agents.security.path_guard import PathGuardAgent
from agents.security.audit_logger import AuditLoggerAgent
from agents.security.anomaly_detector import AnomalyDetectorAgent
from agents.security.gps_stripper import GpsStripperAgent
from agents.security.xmp_stripper import XmpStripperAgent
from agents.security.auth_agent import AuthenticationAgent
from agents.security.dependency_audit import DependencyAuditAgent

# ── Analysis ──────────────────────────────────────────────────────────────
from agents.analysis.scanner import ScannerAgent
from agents.analysis.date_analyzer import DateAnalyzerAgent
from agents.analysis.duplicate_detector import DuplicateDetectorAgent
from agents.analysis.smart_classifier import SmartClassifierAgent

# ── Processing ────────────────────────────────────────────────────────────
from agents.processing.event_matcher import EventMatcherAgent
from agents.processing.folder_manager import FolderManagerAgent
from agents.processing.highlights_curator import HighlightsCuratorAgent
from agents.processing.yearly_best_collector import YearlyBestCollectorAgent

# ── Output ────────────────────────────────────────────────────────────────
from agents.output.checkpoint_manager import CheckpointManagerAgent
from agents.output.report_generator import ReportGeneratorAgent
from agents.output.ui_agent import UIAgent

# ── Core ──────────────────────────────────────────────────────────────────
from core.orchestrator import Orchestrator
from core.event_manager import EventManager
from utils.date_utils import generate_easter_dates

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    # ── 1. CredentialGuardAgent: PRIMA DI TUTTO ───────────────────────────
    credential_guard = CredentialGuardAgent()
    config_path = os.path.join(APP_DIR, 'config.py')
    cred_warnings = credential_guard.check_config(config_path)
    for w in cred_warnings:
        logger.warning("CredentialGuard: %s", w)

    env_errors = credential_guard.check_env_loaded(SOURCE_FOLDER, DESTINATION_FOLDER)
    if env_errors:
        for e in env_errors:
            logger.warning("CredentialGuard: %s", e)
        # Non blocca: usa i valori di default da config.py

    # ── 2. PIL Hardening: configura DecompressionBombGuard ────────────────
    bomb_guard = DecompressionBombGuardAgent(max_pixels=100_000_000)
    bomb_guard.configure()  # già configurato sopra, ma lo applica anche all'agente

    # ── 3. MemoryManagerAgent ─────────────────────────────────────────────
    memory_manager = MemoryManagerAgent(gc_every_n_photos=50)

    # ── 4. Path sicuri ────────────────────────────────────────────────────
    allowed_roots = []
    if SOURCE_FOLDER:
        allowed_roots.append(SOURCE_FOLDER)
    if DESTINATION_FOLDER:
        allowed_roots.append(DESTINATION_FOLDER)
    if not allowed_roots:
        allowed_roots = [APP_DIR]

    path_guard = PathGuardAgent(allowed_roots=allowed_roots)

    # ── 5. AuditLogger ────────────────────────────────────────────────────
    log_path = os.path.join(
        DESTINATION_FOLDER if DESTINATION_FOLDER else APP_DIR,
        AUDIT_LOG_FILE
    )
    audit_logger = AuditLoggerAgent(log_path)

    # ── 6. AnomalyDetector ────────────────────────────────────────────────
    def _on_anomaly(tipo, msg):
        logger.warning("ANOMALIA [%s]: %s", tipo, msg)
        # In GUI: mostrerà toast — collegato in UIAgent

    anomaly_detector = AnomalyDetectorAgent(alert_callback=_on_anomaly)

    # ── 7. DependencyAudit ────────────────────────────────────────────────
    dep_audit = DependencyAuditAgent(app_dir=APP_DIR, audit_logger=audit_logger)
    vulns = dep_audit.run()
    if vulns:
        logger.warning(dep_audit.format_warning(vulns))

    # ── 8. Autenticazione ─────────────────────────────────────────────────
    auth = AuthenticationAgent(app_dir=APP_DIR)

    root = tk.Tk()
    root.withdraw()  # Nasconde finestra principale durante il login

    if auth.is_first_run():
        from ui.auth_dialogs import PinSetupDialog
        dlg = PinSetupDialog(root, auth)
        root.wait_window(dlg)
        if not dlg.result:
            logger.info("Setup PIN annullato — uscita")
            sys.exit(0)
    else:
        from ui.auth_dialogs import LoginDialog
        dlg = LoginDialog(root, auth, anomaly_detector)
        root.wait_window(dlg)
        if not dlg.result:
            logger.info("Login annullato — uscita")
            sys.exit(0)

    # ── 9. Security agents aggiuntivi ─────────────────────────────────────
    file_validator = FileValidatorAgent(max_size_mb=MAX_PHOTO_SIZE_MB)
    exif_sanitizer = ExifSanitizerAgent()
    gps_stripper = GpsStripperAgent()
    xmp_stripper = XmpStripperAgent()

    # ── 10. Analysis agents ───────────────────────────────────────────────
    scanner = ScannerAgent()
    date_analyzer = DateAnalyzerAgent()
    duplicate_detector = DuplicateDetectorAgent(hash_threshold=DUPLICATE_HASH_THRESHOLD)
    smart_classifier = SmartClassifierAgent(use_ai=False)

    # ── 11. Processing agents ─────────────────────────────────────────────
    event_manager = EventManager()
    easter_dates = generate_easter_dates()
    event_matcher = EventMatcherAgent(event_manager, easter_dates)
    folder_manager_agent = FolderManagerAgent(path_guard, audit_logger)
    highlights_curator = HighlightsCuratorAgent()
    yearly_best = YearlyBestCollectorAgent(
        path_guard=path_guard,
        audit_logger=audit_logger,
        count=YEARLY_BEST_COUNT,
        gps_stripper=gps_stripper,
        xmp_stripper=xmp_stripper,
    )

    # ── 12. Output agents ─────────────────────────────────────────────────
    checkpoint_manager = CheckpointManagerAgent(
        checkpoint_path=PROGRESS_FILE,
        path_guard=path_guard,
    )
    report_generator = ReportGeneratorAgent()

    # ── 13. Orchestratore ─────────────────────────────────────────────────
    orchestrator = Orchestrator(
        file_validator=file_validator,
        exif_sanitizer=exif_sanitizer,
        path_guard=path_guard,
        audit_logger=audit_logger,
        scanner=scanner,
        date_analyzer=date_analyzer,
        duplicate_detector=duplicate_detector,
        smart_classifier=smart_classifier,
        event_matcher=event_matcher,
        folder_manager=folder_manager_agent,
        highlights_curator=highlights_curator,
        yearly_best_collector=yearly_best,
        checkpoint_manager=checkpoint_manager,
        report_generator=report_generator,
        anomaly_detector=anomaly_detector,
        memory_manager=memory_manager,
    )

    # ── 14. UI Agent ──────────────────────────────────────────────────────
    root.deiconify()  # Mostra la finestra principale

    # Collega il toast dell'anomaly detector alla GUI
    ui_agent = UIAgent(
        folder_manager_agent=folder_manager_agent,
        path_guard=path_guard,
        auth_agent=auth,
        anomaly_detector=anomaly_detector,
        memory_manager=memory_manager,
        audit_logger=audit_logger,
        dependency_audit=dep_audit,
    )

    # Aggiorna il callback anomaly per usare il toast della GUI
    from ui.components import ToastNotification
    toast = ToastNotification()

    def _on_anomaly_gui(tipo, msg):
        logger.warning("ANOMALIA [%s]: %s", tipo, msg)
        try:
            if root.winfo_exists():
                toast.show(root, f"[{tipo}] {msg}", 'warning', 5000)
        except Exception:
            pass

    anomaly_detector.alert_callback = _on_anomaly_gui

    # Avvia pipeline se SOURCE_FOLDER è configurato
    if SOURCE_FOLDER and os.path.isdir(SOURCE_FOLDER) and DESTINATION_FOLDER:
        logger.info("Avvio pipeline: %s → %s", SOURCE_FOLDER, DESTINATION_FOLDER)
        try:
            stats = orchestrator.run(SOURCE_FOLDER, DESTINATION_FOLDER)
            logger.info("Pipeline completata: %s", stats)
        except Exception as e:
            logger.error("Errore pipeline: %s", e)

    # Avvia GUI
    ui_agent.run()


if __name__ == "__main__":
    main()
