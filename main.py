#!/usr/bin/env python3
"""
Photo Organizer v2 — versione essenziale
Entry point con PIL hardening e pipeline di base.
"""

# ── FASE 1: PIL Hardening (PRIMA DI TUTTO) ────────────────────────────────
import warnings
import os
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = 100_000_000  # 100 MP — decompression bomb protection
warnings.filterwarnings('error', category=Image.DecompressionBombWarning)
ImageFile.LOAD_TRUNCATED_IMAGES = False

# ── Import standard ────────────────────────────────────────────────────────
import logging

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
    AUDIT_LOG_FILE, MAX_PHOTO_SIZE_MB,
)

# ── Agenti ────────────────────────────────────────────────────────────────
from agents.security.file_validator import FileValidatorAgent
from agents.security.path_guard import PathGuardAgent
from agents.security.audit_logger import AuditLoggerAgent
from agents.analysis.scanner import ScannerAgent
from agents.analysis.date_analyzer import DateAnalyzerAgent
from agents.processing.folder_manager import FolderManagerAgent
from agents.output.ui_agent import UIAgent
from core.orchestrator import Orchestrator

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    # ── Path sicuri ───────────────────────────────────────────────────────
    allowed_roots = []
    if SOURCE_FOLDER:
        allowed_roots.append(SOURCE_FOLDER)
    if DESTINATION_FOLDER:
        allowed_roots.append(DESTINATION_FOLDER)
    if not allowed_roots:
        allowed_roots = [APP_DIR]

    path_guard = PathGuardAgent(allowed_roots=allowed_roots)

    # ── Audit logger ──────────────────────────────────────────────────────
    log_path = os.path.join(
        DESTINATION_FOLDER if DESTINATION_FOLDER else APP_DIR,
        AUDIT_LOG_FILE
    )
    audit_logger = AuditLoggerAgent(log_path)

    # ── Agenti principali ─────────────────────────────────────────────────
    file_validator = FileValidatorAgent(max_size_mb=MAX_PHOTO_SIZE_MB)
    scanner = ScannerAgent()
    date_analyzer = DateAnalyzerAgent()
    folder_manager_agent = FolderManagerAgent(path_guard, audit_logger)

    # ── Orchestratore ─────────────────────────────────────────────────────
    orchestrator = Orchestrator(
        file_validator=file_validator,
        path_guard=path_guard,
        audit_logger=audit_logger,
        scanner=scanner,
        date_analyzer=date_analyzer,
        folder_manager=folder_manager_agent,
    )

    # Avvia pipeline se SOURCE_FOLDER è configurato
    if SOURCE_FOLDER and os.path.isdir(SOURCE_FOLDER) and DESTINATION_FOLDER:
        logger.info("Avvio pipeline: %s → %s", SOURCE_FOLDER, DESTINATION_FOLDER)
        try:
            stats = orchestrator.run(SOURCE_FOLDER, DESTINATION_FOLDER)
            logger.info("Pipeline completata: %s", stats)
        except Exception as e:
            logger.error("Errore pipeline: %s", e)

    # ── GUI ───────────────────────────────────────────────────────────────
    ui_agent = UIAgent(
        folder_manager_agent=folder_manager_agent,
        path_guard=path_guard,
        audit_logger=audit_logger,
    )
    ui_agent.run()


if __name__ == "__main__":
    main()
