# MIGRATION.md — Guida alla Migrazione da v1 a v2

## Cosa cambia per l'utente finale

Niente di visibile: le cartelle di output hanno gli stessi nomi emoji,
`config.py` si modifica nello stesso modo, `file_eventi.txt` ha lo stesso formato.

La differenza è interna: il codice è più sicuro, più veloce e trova i duplicati.

---

## Nuove cartelle nell'output

```
📂 Destinazione/
├── ⭐ HIGHLIGHTS/          ← invariato
├── 📅 EVENTI/              ← invariato
├── 📸 ARCHIVIO/            ← invariato
├── 🖨️ DA_STAMPARE/         ← invariato
├── 📅 MIGLIORI_ANNO/       ← NUOVO
│   ├── 2022_best_12/
│   ├── 2023_best_12/
│   └── 2024_best_12/
└── audit_log.txt           ← NUOVO (non cancellare!)
```

---

## Costanti da aggiungere a config.py

Aggiungi queste righe **in fondo** al `config.py` esistente, senza toccare nulla di ciò che c'è già:

```python
# ── Yearly Best Collector ──────────────────────────────────────
YEARLY_BEST_FOLDER_NAME = "📅 MIGLIORI_ANNO"
YEARLY_BEST_COUNT = 12          # numero di foto per anno, modifica a piacere

# ── Sicurezza ──────────────────────────────────────────────────
AUDIT_LOG_FILE = "audit_log.txt"
MAX_PHOTO_SIZE_MB = 200         # file più grandi vengono ignorati

# ── Duplicati ──────────────────────────────────────────────────
DUPLICATE_HASH_THRESHOLD = 8    # distanza Hamming per perceptual hash (0=identici)
```

---

## Aggiornamento requirements.txt

Sostituisci il `requirements.txt` esistente con:

```
Pillow>=10.0.0
imagehash>=4.3.1
pytest>=8.0.0
```

Installa con:
```bash
pip install -r requirements.txt
```

---

## Aggiornamento main.py

Il nuovo `main.py` deve:

1. Importare e istanziare tutti gli agenti
2. Passarli all'Orchestratore via dependency injection
3. Chiamare `orchestrator.run(source, destination)`
4. Avviare la GUI via `UIAgent`

**Schema del nuovo main.py**:

```python
from config import SOURCE_FOLDER, DESTINATION_FOLDER, AUDIT_LOG_FILE, \
    YEARLY_BEST_COUNT, MAX_PHOTO_SIZE_MB, DUPLICATE_HASH_THRESHOLD

from agents.security.file_validator import FileValidatorAgent
from agents.security.exif_sanitizer import ExifSanitizerAgent
from agents.security.path_guard import PathGuardAgent
from agents.security.audit_logger import AuditLoggerAgent

from agents.analysis.scanner import ScannerAgent
from agents.analysis.date_analyzer import DateAnalyzerAgent
from agents.analysis.duplicate_detector import DuplicateDetectorAgent
from agents.analysis.smart_classifier import SmartClassifierAgent

from agents.processing.event_matcher import EventMatcherAgent
from agents.processing.folder_manager import FolderManagerAgent
from agents.processing.highlights_curator import HighlightsCuratorAgent
from agents.processing.yearly_best_collector import YearlyBestCollectorAgent

from agents.output.checkpoint_manager import CheckpointManagerAgent
from agents.output.report_generator import ReportGeneratorAgent
from agents.output.ui_agent import UIAgent

from core.orchestrator import Orchestrator
from utils.date_utils import generate_easter_dates
from core.event_manager import EventManager
import os

def main():
    # Security
    path_guard = PathGuardAgent(allowed_roots=[SOURCE_FOLDER, DESTINATION_FOLDER])
    audit_logger = AuditLoggerAgent(os.path.join(DESTINATION_FOLDER, AUDIT_LOG_FILE))
    file_validator = FileValidatorAgent(max_size_mb=MAX_PHOTO_SIZE_MB)
    exif_sanitizer = ExifSanitizerAgent()

    # Analysis
    scanner = ScannerAgent()
    date_analyzer = DateAnalyzerAgent()
    duplicate_detector = DuplicateDetectorAgent(hash_threshold=DUPLICATE_HASH_THRESHOLD)
    smart_classifier = SmartClassifierAgent(use_ai=False)  # True se hai le librerie AI

    # Processing
    event_manager = EventManager()
    easter_dates = generate_easter_dates()
    event_matcher = EventMatcherAgent(event_manager, easter_dates)
    folder_manager_agent = FolderManagerAgent(path_guard, audit_logger)
    highlights_curator = HighlightsCuratorAgent()
    yearly_best = YearlyBestCollectorAgent(path_guard, audit_logger, count=YEARLY_BEST_COUNT)

    # Output
    checkpoint_manager = CheckpointManagerAgent(
        checkpoint_path='progress_checkpoint.txt',
        path_guard=path_guard
    )
    report_generator = ReportGeneratorAgent()

    # Orchestratore
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
    )

    # Run pipeline + GUI
    stats = orchestrator.run(SOURCE_FOLDER, DESTINATION_FOLDER)

    ui = UIAgent(
        photo_manager=orchestrator.photo_manager,
        folder_manager_agent=folder_manager_agent,
        path_guard=path_guard,
    )
    ui.run()

if __name__ == '__main__':
    main()
```

---

## Compatibilità checkpoint

Il nuovo `CheckpointManagerAgent` è compatibile con i checkpoint salvati dalla v1.
Se esiste già un `progress_checkpoint.txt`, viene letto e migrato automaticamente
(ogni path viene validato con PathGuard; i path invalidi vengono ignorati con un warning).

---

## Come eseguire i test

```bash
cd Organizza_Foto
pytest tests/ -v
```

Output atteso:
```
tests/test_file_validator.py::test_valid_jpeg PASSED
tests/test_file_validator.py::test_executable_renamed_jpg PASSED
tests/test_path_guard.py::test_safe_join_traversal PASSED
...
```
