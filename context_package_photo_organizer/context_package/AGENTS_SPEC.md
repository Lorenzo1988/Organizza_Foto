# AGENTS_SPEC.md — Specifica di ogni Agente

Interfacce, comportamenti e note implementative per tutti i 17 agenti.

---

## LAYER 1 — Security Gate

### FileValidatorAgent
**File**: `agents/security/file_validator.py`

```python
class FileValidatorAgent:
    def __init__(self, max_size_mb: int = 200): ...
    def validate(self, file_path: str) -> bool: ...
    def get_errors(self) -> list[str]: ...
```

- Controlla in ordine: esistenza file → estensione nella whitelist →
  dimensione > 0 e < max → magic bytes corrispondenti
- `get_errors()` ritorna la lista degli errori dell'ultima chiamata a `validate()`
- Non lancia eccezioni: ritorna sempre `True` o `False`

**Magic bytes supportati**:
JPEG (`\xff\xd8\xff`), PNG (`\x89PNG`), GIF87a, GIF89a, BMP (`BM`),
TIFF little-endian (`II*\x00`), TIFF big-endian (`MM\x00*`),
HEIC (`\x00\x00\x00\x0cftyp`, `ftypheic`, `ftypmif1`)

---

### ExifSanitizerAgent
**File**: `agents/security/exif_sanitizer.py`

```python
class ExifSanitizerAgent:
    def sanitize(self, file_path: str) -> dict: ...
```

**Struttura del dizionario ritornato**:
```python
{
    'date': datetime | None,      # data di scatto
    'source': str,                # 'exif' | 'none'
    'gps': {'lat': float, 'lon': float} | None,
    'make': str | None,           # marca fotocamera
    'model': str | None,          # modello fotocamera
    'orientation': int,           # 1-8, default 1
}
```

- Whitelist tag: `DateTimeOriginal`, `DateTime`, `DateTimeDigitized`,
  `GPSInfo`, `Make`, `Model`, `Orientation`, `ImageWidth`, `ImageLength`
- Valori sanitizzati: solo `int`, `float`, `str` (max 256 chars, solo printable),
  `tuple/list` di numerici
- Non lancia mai eccezioni: ritorna dict con tutti i campi a None in caso di errore

---

### PathGuardAgent
**File**: `agents/security/path_guard.py`

```python
class PathGuardAgent:
    def __init__(self, allowed_roots: list[str]): ...
    def is_safe_path(self, path: str) -> bool: ...
    def safe_join(self, base: str, *parts: str) -> str: ...
    def validate_highlight_name(self, name: str) -> str: ...
    def add_allowed_root(self, path: str): ...
```

- `allowed_roots` vengono risolti con `Path.resolve()` all'inizializzazione
- `safe_join()` lancia `ValueError` se il path risultante esce dalla sandbox
- `validate_highlight_name()` accetta solo alfanumerici + spazio + `_-` + lettere accentate
- Lunghezza massima nome highlight: 100 caratteri

---

### AuditLoggerAgent
**File**: `agents/security/audit_logger.py`

```python
class AuditLoggerAgent:
    def __init__(self, log_path: str): ...
    def log_move(self, src: str, dst: str): ...
    def log_copy(self, src: str, dst: str): ...
    def log_delete(self, path: str): ...
    def log_skip(self, path: str, reason: str | list): ...
    def log_event(self, event: str, detail: str = ''): ...
```

**Formato di ogni riga del log**:
```
2025-10-12T14:23:01.123456 | MOVE | /src/foto.jpg -> /dst/2025_Estate/foto.jpg | md5=a1b2c3d4
2025-10-12T14:23:01.234567 | SKIP | /src/evil.jpg | motivo=Magic bytes non validi
```

- File aperto in modalità `'a'` (append): non sovrascrive mai
- Hash calcolato sui primi 64KB del file (veloce, sufficiente per identificazione)
- `log_skip()` accetta sia `str` che `list[str]` per il motivo
- Thread-safe: usa un `threading.Lock` interno

---

## LAYER 2 — Analisi

### ScannerAgent
**File**: `agents/analysis/scanner.py`

```python
class ScannerAgent:
    def __init__(self, extensions: set[str] = None): ...
    def scan(self, folder: str) -> list[str]: ...
```

- Ricicla la logica di `utils/file_utils.py:load_all_photos()`
- Ritorna lista di path ordinata
- Estensioni default: quelle in `config.PHOTO_EXTENSIONS`

---

### DateAnalyzerAgent
**File**: `agents/analysis/date_analyzer.py`

```python
class DateAnalyzerAgent:
    def analyze(self, meta: PhotoMetadata, exif: dict) -> PhotoMetadata: ...
```

**Priorità di estrazione data**:
1. `exif['date']` (già estratto e sanitizzato da ExifSanitizerAgent)
2. Data nel filename (pattern `YYYYMMDD`, `YYYY-MM-DD`, `YYYY_MM_DD`)
3. Data di modifica del file (`os.path.getmtime`)

Imposta `meta.date` e `meta.date_source` ('exif' | 'filename' | 'mtime').

---

### DuplicateDetectorAgent
**File**: `agents/analysis/duplicate_detector.py`

```python
class DuplicateDetectorAgent:
    def __init__(self, hash_threshold: int = 8): ...
    def check(self, meta: PhotoMetadata) -> PhotoMetadata: ...
    def clear_cache(self): ...
```

**Strategia di rilevamento duplicati**:
1. Calcola MD5 dell'intero file → match esatto
2. Se `imagehash` disponibile: calcola pHash (perceptual hash) →
   match visivo (immagini quasi identiche, diverse compressioni)
3. Mantiene un dizionario interno `{hash: path}` tra le chiamate
4. Se duplicato trovato: imposta `meta.is_duplicate = True` e
   `meta.duplicate_of = path_originale`

- `hash_threshold`: distanza di Hamming massima per il pHash (default 8)
- Fallback graceful se `imagehash` non è installato (usa solo MD5)

---

### SmartClassifierAgent
**File**: `agents/analysis/smart_classifier.py`

```python
class SmartClassifierAgent:
    def __init__(self, use_ai: bool = True): ...
    def classify(self, meta: PhotoMetadata) -> PhotoMetadata: ...
```

**Modalità AI** (se `use_ai=True` e librerie disponibili):
- Usa `transformers` + modello CLIP per generare tag semantici
- Tag esempio: `['spiaggia', 'estate', 'persone', 'tramonto']`
- Imposta `meta.tags` e `meta.quality_score` (0.0–1.0)

**Modalità fallback** (se AI non disponibile):
- Inferisce tag dal nome file e dalla cartella sorgente
- `quality_score` basato su dimensione file (proxy per qualità)
- Non lancia mai eccezioni

---

## LAYER 3 — Elaborazione

### EventMatcherAgent
**File**: `agents/processing/event_matcher.py`

```python
class EventMatcherAgent:
    def __init__(self, event_manager, easter_dates: dict): ...
    def match(self, meta: PhotoMetadata) -> PhotoMetadata: ...
```

- Wrappa la logica di `core/event_manager.py` e `core/folder_manager.py:determine_folder()`
- Imposta `meta.event_name` e `meta.event_priority`
- Compatibile con `file_eventi.txt` esistente

---

### FolderManagerAgent
**File**: `agents/processing/folder_manager.py`

```python
class FolderManagerAgent:
    def __init__(self, path_guard: PathGuardAgent, audit_logger: AuditLoggerAgent): ...
    def organize(self, meta: PhotoMetadata, destination: str) -> str: ...
    def move_to_highlight(self, meta: PhotoMetadata, highlight_name: str) -> str: ...
    def get_existing_highlights(self, destination: str) -> list[str]: ...
```

- Wrappa `core/folder_manager.py` aggiungendo PathGuard e AuditLogger
- **Usa copy-then-verify-then-delete** invece di `shutil.move` diretto
- Ritorna il nuovo path della foto dopo lo spostamento

---

### HighlightsCuratorAgent
**File**: `agents/processing/highlights_curator.py`

```python
class HighlightsCuratorAgent:
    def __init__(self, quality_threshold: float = 0.7): ...
    def should_promote(self, meta: PhotoMetadata) -> bool: ...
    def promote(self, meta: PhotoMetadata, highlight_name: str,
                folder_manager: FolderManagerAgent) -> PhotoMetadata: ...
```

**Criteri di promozione automatica**:
- `meta.quality_score >= quality_threshold`
- Oppure: foto già contrassegnata come highlight dall'utente nella GUI

---

### YearlyBestCollectorAgent
**File**: `agents/processing/yearly_best_collector.py`

```python
class YearlyBestCollectorAgent:
    def __init__(self, path_guard: PathGuardAgent, audit_logger: AuditLoggerAgent,
                 count: int = 12): ...
    def collect(self, destination: str) -> dict[int, list[str]]: ...
```

**Logica**:
1. Scansiona `{destination}/⭐ HIGHLIGHTS/` ricorsivamente
2. Per ogni foto, estrae l'anno dalla data nel nome file o EXIF
3. Raggruppa per anno
4. Per ogni anno, ordina per `quality_score` (desc) poi per data (asc)
5. Prende le prime `count` foto
6. Le **copia** (non sposta) in `{destination}/📅 MIGLIORI_ANNO/{anno}_best_{count}/`
7. Se la cartella esiste già, aggiunge solo le foto mancanti (idempotente)
8. Ritorna un dict `{anno: [lista_path_copiate]}`

**Costanti da aggiungere in config.py**:
```python
YEARLY_BEST_FOLDER_NAME = "📅 MIGLIORI_ANNO"
YEARLY_BEST_COUNT = 12
```

---

## LAYER 4 — Output

### CheckpointManagerAgent
**File**: `agents/output/checkpoint_manager.py`

```python
class CheckpointManagerAgent:
    def __init__(self, checkpoint_path: str, path_guard: PathGuardAgent): ...
    def save(self, meta: PhotoMetadata): ...
    def load(self) -> list[str]: ...
    def clear(self): ...
    def exists(self) -> bool: ...
```

- Valida ogni path letto con `path_guard.is_safe_path()` prima di usarlo
- Compatibile con il formato del checkpoint originale

---

### ReportGeneratorAgent
**File**: `agents/output/report_generator.py`

```python
class ReportGeneratorAgent:
    def generate(self, stats: dict, destination: str) -> str: ...
```

**Output**: file HTML in `{destination}/report_{timestamp}.html` con:
- Totale foto processate, spostate, duplicate, errori
- Breakdown per anno e per evento
- Lista highlights creati
- Durata esecuzione

---

### UIAgent
**File**: `agents/output/ui_agent.py`

```python
class UIAgent:
    def __init__(self, photo_manager, folder_manager_agent,
                 path_guard: PathGuardAgent): ...
    def run(self): ...
```

- Wrappa `ui/main_window.py` esistente
- Aggiunge: barra progresso, contatore duplicati saltati,
  pulsante "Vedi Yearly Best"
- **Tutte le operazioni da UI passano per PathGuard**

---

### ExportAgent
**File**: `agents/output/export_agent.py`

```python
class ExportAgent:
    def __init__(self, path_guard: PathGuardAgent, audit_logger: AuditLoggerAgent): ...
    def export_to_folder(self, source: str, dest: str) -> int: ...
```

- Copia l'intera struttura organizzata in una cartella di export
- Ritorna il numero di file copiati

---

## Agenti nuovi (da ricerca standard OWASP + PIL)

### DecompressionBombGuardAgent
**File**: `agents/security/decompression_bomb_guard.py`
**Vedi**: PIL_HARDENING.md — Problema 1

```python
class DecompressionBombGuardAgent:
    def __init__(self, max_pixels: int = 100_000_000): ...
    def configure(self): ...          # chiama PRIMA di tutto in main.py
    def safe_open(self, path: str) -> Image.Image | None: ...
```

Configura `Image.MAX_IMAGE_PIXELS` e converte `DecompressionBombWarning`
in errore bloccante. `safe_open()` sostituisce ogni `Image.open()` diretto.

---

### MemoryManagerAgent
**File**: `agents/security/memory_manager.py`
**Vedi**: PIL_HARDENING.md — Problema 2

```python
class MemoryManagerAgent:
    def __init__(self, gc_every_n_photos: int = 50): ...
    def open_image(self, file_path: str): ...        # context manager
    def open_thumbnail(self, file_path: str, max_size=(800,600)) -> Image.Image | None: ...
    def force_gc(self): ...
```

Tutti i `Image.open()` nel progetto devono passare per questo agente.

---

### XmpStripperAgent
**File**: `agents/security/xmp_stripper.py`
**Vedi**: PIL_HARDENING.md — Problema 4

```python
class XmpStripperAgent:
    def strip_xmp(self, source_path: str, dest_path: str) -> bool: ...
    def should_strip(self, destination_path: str) -> bool: ...
```

Complementa GpsStripperAgent per i metadati XMP (Adobe).
Attivato nelle stesse cartelle di GpsStripperAgent.

---

### DependencyAuditAgent
**File**: `agents/security/dependency_audit.py`
**Vedi**: SUPPLY_CHAIN.md

```python
class DependencyAuditAgent:
    def __init__(self, app_dir: str, audit_logger=None): ...
    def should_run(self) -> bool: ...
    def run(self) -> list[dict]: ...
    def format_warning(self, vulnerabilities: list[dict]) -> str: ...
```

Esegue `pip-audit` max una volta ogni 7 giorni. Non bloccante.

---

### AnomalyDetectorAgent
**File**: `agents/security/anomaly_detector.py`
**Vedi**: MONITORING.md

```python
class AnomalyDetectorAgent:
    def __init__(self, alert_callback: Callable[[str, str], None] = None): ...
    def on_delete(self, path: str): ...
    def on_traversal_attempt(self, path: str): ...
    def on_auth_failure(self, attempt_number: int): ...
    def reset(self): ...
```

Monitora pattern anomali. `alert_callback` mostra toast nella GUI.

---

## Aggiornamenti agenti esistenti

### AuthenticationAgent → v2
**Vedi**: AUTHENTICATION_V2.md (sostituisce AUTHENTICATION.md)
- bcrypt (cost 12) invece di SHA-256
- keyring per storage OS Keychain invece di file
- bytearray per PIN invece di str (azzerabile)

### ExifSanitizerAgent — fix API
Sostituire `image._getexif()` con `image.getexif()` + `get_ifd(0x8825)` per GPS.

### AuditLoggerAgent → v2
**Vedi**: MONITORING.md
- Formato JSON strutturato invece di testo libero
- RotatingFileHandler (5MB, 3 backup)
- Nessun path assoluto nel log (solo nome file + hash MD5 abbreviato)
