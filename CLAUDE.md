# CLAUDE.md — Photo Organizer v2

Istruzioni specifiche per questo progetto. Si applicano a chiunque lavori su questo repo.

## Regola branch e PR — OBBLIGATORIA

**Prima di qualsiasi modifica al codice:**
1. `git checkout -b <nome-branch>` — creare un branch dedicato
2. Fare il commit sul branch
3. Aprire una Pull Request verso `main` con `gh pr create`

## Architettura

Pipeline lineare con dependency injection:

```
Validazione → Analisi data → Organizzazione cartelle → GUI
```

L'orchestratore (`core/orchestrator.py`) è il solo punto che li connette.

## Agenti attivi

```
agents/
  security/   — file_validator, path_guard, audit_logger
  analysis/   — scanner, date_analyzer
  processing/ — folder_manager
  output/     — ui_agent

core/
  orchestrator.py   — PhotoMetadata dataclass + Orchestrator (DI)
  event_manager.py  — gestione eventi personalizzati

ui/
  components.py     — PhotoProgressBar, ToastNotification, ActionButton, InfoBar, StatusBar
```

## Regole critiche — NON violare mai

### PIL / Immagini
- `Image.MAX_IMAGE_PIXELS` e `warnings.filterwarnings('error', ...)` devono stare in `main.py` **prima di qualsiasi altro import**.
- `ImageFile.LOAD_TRUNCATED_IMAGES = False` — non cambiare.
- Nella GUI (`ui_agent.py`): aprire le immagini sempre con `with Image.open(...) as img` e fare `img.thumbnail()` prima di copiare.

### File system
- Ogni path → `path_guard.safe_join()` prima dell'uso.
- Ogni delete → `send2trash` (mai `os.remove` o `shutil.rmtree`).
- Ogni operazione FS rilevante → `audit_logger.log_event()` prima di eseguire.

### Config
- Aggiunte in fondo a `config.py` — non riordinare le costanti esistenti.
- Percorsi sensibili (`SOURCE_FOLDER`, `DESTINATION_FOLDER`) caricati da `.env` tramite `python-dotenv`.

## PhotoMetadata

Il dataclass centrale in `core/orchestrator.py`:

```python
@dataclass
class PhotoMetadata:
    original_path: str
    current_path: str
    date: Optional[datetime]
    date_source: str          # 'exif' | 'filename' | 'mtime'
    is_duplicate: bool
    duplicate_of: Optional[str]
    tags: List[str]
    event_name: Optional[str]
    event_priority: int
    is_highlight: bool
    highlight_name: Optional[str]
    quality_score: float
    exif_data: dict
    gps: Optional[dict]
```

## Feature stub (non ancora implementate)

- `UIAgent._skip_photo()` — solo `logger.debug`
- `UIAgent._go_back()` — solo `logger.debug`

## Test

```bash
pytest tests/ -v
```

Test attivi in `tests/`: `test_audit_logger`, `test_file_validator`, `test_path_guard`, `test_pil_hardening`.

## Dipendenze principali

- `Pillow` — immagini
- `send2trash` — eliminazione sicura
- `python-dotenv` — variabili d'ambiente
