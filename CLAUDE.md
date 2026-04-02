# CLAUDE.md — Photo Organizer v2

Istruzioni specifiche per questo progetto. Si applicano a chiunque lavori su questo repo.

## Architettura

4 layer con dependency injection, nessuna dipendenza circolare tra layer:

```
Security Gate → Analysis → Processing → Output
```

L'orchestratore (`core/orchestrator.py`) è il solo punto che li connette.

## Regole critiche — NON violare mai

### PIL / Immagini
- `Image.MAX_IMAGE_PIXELS` e `warnings.filterwarnings('error', ...)` devono stare in `main.py` **prima di qualsiasi altro import**.
- Nella GUI: usa **sempre** `memory_manager.open_thumbnail()`, mai `Image.open()` diretto.
- `ImageFile.LOAD_TRUNCATED_IMAGES = False` — non cambiare.

### File system
- Ogni path → `path_guard.safe_join()` prima dell'uso.
- Ogni delete → `send2trash` (mai `os.remove` o `shutil.rmtree`).
- Ogni operazione FS rilevante → `audit_logger.log_event()` prima di eseguire.

### EXIF / Metadati
- `ExifSanitizerAgent` usa `getexif()`, **mai** `_getexif()` (deprecata, unsafe).
- GPS e XMP vengono rimossi da `GpsStripperAgent` e `XmpStripperAgent` prima di copiare.

### Autenticazione
- PIN come `bytearray` azzerabile dopo l'uso — mai come `str` plain.
- `AuthenticationAgent`: bcrypt cost factor 12 + keyring.
- Timeout sessione: 5 min, controllato in `UIAgent._check_session_timeout()`.

### Config
- Aggiunte in fondo a `config.py` — non riordinare le costanti esistenti.
- Percorsi sensibili (`SOURCE_FOLDER`, `DESTINATION_FOLDER`) caricati da `.env` tramite `python-dotenv`.

## Struttura agenti

```
agents/
  security/   — 12 agenti (credential_guard, memory_manager, file_validator,
                            exif_sanitizer, path_guard, audit_logger,
                            anomaly_detector, gps_stripper, xmp_stripper,
                            auth_agent, dependency_audit, decompression_bomb_guard)
  analysis/   — scanner, date_analyzer, duplicate_detector, smart_classifier
  processing/ — event_matcher, folder_manager, highlights_curator, yearly_best_collector
  output/     — checkpoint_manager, report_generator, export_agent, ui_agent

core/
  orchestrator.py   — PhotoMetadata dataclass + Orchestrator (DI)
  event_manager.py  — gestione eventi personalizzati

ui/
  auth_dialogs.py   — PinSetupDialog, LoginDialog, LockScreenDialog
  components.py     — PhotoProgressBar, ToastNotification, ActionButton, InfoBar, StatusBar
```

## PhotoMetadata

Il dataclass centrale arricchito da ogni agente del layer Analysis/Processing:

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
    quality_score: float      # 0.0–1.0
    exif_data: dict
    gps: Optional[dict]
```

## Feature non ancora implementate (stub)

- `UIAgent._skip_photo()` — solo `logger.debug`
- `UIAgent._go_back()` — solo `logger.debug`
- Bottone "Genera raccolta" in `ui_agent.py:161` — manca `command`
- `export_agent.py` — esiste ma non integrato nella GUI
- `SmartClassifierAgent` — istanziato con `use_ai=False`

## Test

```bash
pytest tests/ -v
```

75/75 test in `tests/`. Ogni nuovo agente deve avere test in `tests/`.

## Dipendenze principali

- `Pillow` — immagini
- `piexif` — stripping EXIF/GPS/XMP
- `imagehash` — perceptual hash per duplicati
- `bcrypt` + `keyring` — autenticazione PIN
- `send2trash` — eliminazione sicura
- `python-dotenv` — variabili d'ambiente
- `pip-audit` — CVE scan dipendenze (max 1 run/settimana)
