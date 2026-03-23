# ARCHITECTURE.md — Architettura Multi-Agente

## Overview

Il sistema è organizzato in 4 layer sequenziali + 1 layer trasversale (sicurezza).
Ogni file attraversa obbligatoriamente il Security Gate prima di qualsiasi elaborazione.

```
[Foto sorgente]
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Security Gate (bloccante)                        │
│  FileValidator → ExifSanitizer → PathGuard                  │
│                         ↕ (trasversale)                     │
│                    AuditLogger                              │
└─────────────────────────────────────────────────────────────┘
      │ file OK
      ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — Analisi (parallela, read-only)                   │
│  Scanner │ DateAnalyzer │ DuplicateDetector │ SmartClassifier│
└─────────────────────────────────────────────────────────────┘
      │ PhotoMetadata
      ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Elaborazione (scrittura su filesystem)           │
│  EventMatcher │ FolderManager │ HighlightsCurator           │
│                    YearlyBestCollector                      │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — Output                                           │
│  CheckpointManager │ ReportGenerator │ UIAgent │ ExportAgent│
└─────────────────────────────────────────────────────────────┘
      │
      ▼
[Libreria organizzata + audit log + report]
```

---

## Oggetto centrale: PhotoMetadata

Ogni agente del Layer 2 arricchisce un oggetto `PhotoMetadata` che viene
passato ai layer successivi. Definiscilo in `core/orchestrator.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class PhotoMetadata:
    original_path: str
    current_path: str
    date: datetime | None = None
    date_source: str = 'unknown'      # 'exif', 'filename', 'mtime'
    is_duplicate: bool = False
    duplicate_of: str | None = None
    tags: list[str] = field(default_factory=list)
    event_name: str | None = None
    event_priority: int = 0
    is_highlight: bool = False
    highlight_name: str | None = None
    quality_score: float = 0.0        # 0.0–1.0, usato da HighlightsCurator
    exif_data: dict = field(default_factory=dict)
    gps: dict | None = None
```

---

## Orchestratore

L'Orchestratore (`core/orchestrator.py`) riceve tutti gli agenti via
dependency injection nel costruttore e coordina il flusso:

```python
class Orchestrator:
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
    ):
        ...

    def run(self, source_folder: str, destination_folder: str) -> dict:
        """
        Esegue la pipeline completa. Ritorna un dizionario di statistiche.
        """
        ...
```

### Flusso interno dell'Orchestratore

```python
def run(self, source_folder, destination_folder):
    stats = {'total': 0, 'moved': 0, 'duplicates': 0, 'errors': 0, 'highlights': 0}

    # 1. Scansione
    all_files = self.scanner.scan(source_folder)
    stats['total'] = len(all_files)

    for file_path in all_files:
        try:
            # 2. Security Gate (bloccante)
            if not self.file_validator.validate(file_path):
                self.audit_logger.log_skip(file_path, self.file_validator.get_errors())
                stats['errors'] += 1
                continue

            exif = self.exif_sanitizer.sanitize(file_path)

            # 3. Analisi
            meta = PhotoMetadata(original_path=file_path, current_path=file_path)
            meta = self.date_analyzer.analyze(meta, exif)
            meta = self.duplicate_detector.check(meta)
            meta = self.smart_classifier.classify(meta)

            if meta.is_duplicate:
                self.audit_logger.log_skip(file_path, 'duplicato')
                stats['duplicates'] += 1
                continue

            # 4. Elaborazione
            meta = self.event_matcher.match(meta)
            new_path = self.folder_manager.organize(meta, destination_folder)
            self.audit_logger.log_move(file_path, new_path)
            meta.current_path = new_path
            stats['moved'] += 1

            # 5. Checkpoint
            self.checkpoint_manager.save(meta)

        except Exception as e:
            self.audit_logger.log_skip(file_path, f'errore: {e}')
            stats['errors'] += 1

    # 6. Raccolta annuale highlights
    self.yearly_best_collector.collect(destination_folder)

    # 7. Report
    self.report_generator.generate(stats, destination_folder)

    return stats
```

---

## YearlyBestCollector — logica dettagliata

Questo agente è nuovo e specifico per la raccolta annuale.

### Comportamento atteso

- Scansiona la cartella `⭐ HIGHLIGHTS/` nella destination
- Raggruppa le foto per anno di scatto (dalla data nel nome file o EXIF)
- Per ogni anno crea (o aggiorna) la cartella:
  `📅 MIGLIORI_ANNO/{anno}_best_{N}/`
  dove N è configurabile (default: 12)
- **Non sposta** le foto originali dagli HIGHLIGHTS — le **copia**
- Se la cartella esiste già, aggiorna solo le foto mancanti (idempotente)
- Ordina le foto per qualità (se disponibile) o per data

### Configurazione

```python
# In config.py da aggiungere:
YEARLY_BEST_FOLDER_NAME = "📅 MIGLIORI_ANNO"
YEARLY_BEST_COUNT = 12   # numero di foto per anno, modificabile
```

### Struttura output

```
📅 MIGLIORI_ANNO/
├── 2022_best_12/
│   ├── foto1.jpg
│   ├── foto2.jpg
│   └── ...
├── 2023_best_12/
│   └── ...
└── 2024_best_12/
    └── ...
```

---

## Gestione errori

Ogni agente deve:
1. Non lanciare eccezioni non gestite verso l'Orchestratore
2. Loggare gli errori internamente e ritornare un risultato "safe" (es. `False`, dict vuoto)
3. Eccezione: `PathGuardAgent` **deve** lanciare `ValueError` — è l'unico agente
   il cui errore deve fermare immediatamente l'operazione

---

## Compatibilità con il codice esistente

| File originale | Azione |
|---|---|
| `config.py` | Invariato — aggiungi solo le nuove costanti in fondo |
| `file_eventi.txt` | Invariato |
| `utils/date_utils.py` | Invariato |
| `utils/file_utils.py` | Invariato — usato internamente dagli agenti |
| `core/event_manager.py` | Wrappato da EventMatcherAgent |
| `core/folder_manager.py` | Wrappato da FolderManagerAgent |
| `core/photo_manager.py` | Wrappato da CheckpointManagerAgent |
| `ui/main_window.py` | Wrappato da UIAgent, minime modifiche |
