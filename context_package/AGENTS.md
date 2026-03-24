# AGENTS.md — Istruzioni per Claude Code
# Photo Organizer v2 — Architettura Multi-Agente

Leggi questo file per intero prima di scrivere qualsiasi codice.
Poi leggi in ordine: ARCHITECTURE.md, SECURITY.md, AGENTS_SPEC.md, MIGRATION.md.

---

## Obiettivo

Costruire una versione potenziata del progetto `Organizza_Foto` esistente,
trasformandolo in un'architettura multi-agente con sicurezza integrata,
rilevamento duplicati, classificazione AI e raccolta annuale delle migliori foto.

## File da leggere in ordine (aggiornato)

Leggi questi file in ordine prima di scrivere codice:
1. AGENTS.md (questo file)
2. ARCHITECTURE.md
3. SECURITY.md
4. SECURITY_AUDIT.md
5. AUTHENTICATION_V2.md  ← usa questo, non AUTHENTICATION.md
6. PIL_HARDENING.md      ← NUOVO
7. SUPPLY_CHAIN.md       ← NUOVO
8. MONITORING.md         ← NUOVO
9. PRIVACY_SECURITY.md
10. AGENTS_SPEC.md
11. MIGRATION.md
12. UI_DESIGN.md

---

## Regole generali

1. **Non rompere la compatibilità**: `config.py` e `file_eventi.txt` restano invariati.
2. **Ogni agente è una classe autonoma** in un file dedicato sotto `agents/`.
3. **Il Security Gate è obbligatorio**: nessun file entra nella pipeline senza passare
   per FileValidatorAgent, ExifSanitizerAgent, PathGuardAgent.
4. **AuditLoggerAgent è trasversale**: viene iniettato nell'Orchestratore e
   ogni operazione su filesystem (move, copy, delete) deve passare da lui.
5. **Tutti i path passano per PathGuardAgent.safe_join()** — mai os.path.join diretto
   quando si costruiscono percorsi di destinazione.
6. **Scrivi i test** per tutti gli agenti del Layer 1 (Security Gate) in `tests/`.
7. **Mantieni i nomi delle cartelle emoji** già presenti nel config originale.
8. **La GUI tkinter esistente va mantenuta** e potenziata, non riscritta da zero.

## Struttura da creare

```
Organizza_Foto/
├── AGENTS.md                    ← questo file
├── ARCHITECTURE.md
├── SECURITY.md
├── AGENTS_SPEC.md
├── MIGRATION.md
├── config.py                    ← INVARIATO (esiste già)
├── file_eventi.txt              ← INVARIATO (esiste già)
├── main.py                      ← da aggiornare per usare Orchestratore
├── requirements.txt             ← da aggiornare con nuove dipendenze
│
├── agents/
│   ├── __init__.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── file_validator.py    ← FileValidatorAgent
│   │   ├── exif_sanitizer.py   ← ExifSanitizerAgent
│   │   ├── path_guard.py       ← PathGuardAgent
│   │   ├── audit_logger.py     ← AuditLoggerAgent
│   │   ├── credential_guard.py    ← CredentialGuardAgent
│   │   ├── gps_stripper.py        ← GpsStripperAgent
│   │   ├── xmp_stripper.py        ← XmpStripperAgent (NUOVO)
│   │   ├── decompression_bomb_guard.py ← DecompressionBombGuardAgent (NUOVO)
│   │   ├── memory_manager.py      ← MemoryManagerAgent (NUOVO)
│   │   ├── anomaly_detector.py    ← AnomalyDetectorAgent (NUOVO)
│   │   └── dependency_audit.py    ← DependencyAuditAgent (NUOVO)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── scanner.py           ← ScannerAgent
│   │   ├── date_analyzer.py    ← DateAnalyzerAgent
│   │   ├── duplicate_detector.py ← DuplicateDetectorAgent
│   │   └── smart_classifier.py ← SmartClassifierAgent
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── event_matcher.py    ← EventMatcherAgent
│   │   ├── folder_manager.py   ← FolderManagerAgent
│   │   ├── highlights_curator.py ← HighlightsCuratorAgent
│   │   └── yearly_best_collector.py ← YearlyBestCollectorAgent
│   └── output/
│       ├── __init__.py
│       ├── checkpoint_manager.py ← CheckpointManagerAgent
│       ├── report_generator.py  ← ReportGeneratorAgent
│       ├── ui_agent.py          ← UIAgent (GUI tkinter)
│       └── export_agent.py     ← ExportAgent
│
├── core/
│   ├── __init__.py
│   └── orchestrator.py         ← Orchestratore centrale
│
├── utils/
│   ├── __init__.py
│   ├── date_utils.py           ← INVARIATO (esiste già)
│   └── file_utils.py           ← INVARIATO (esiste già)
│
└── tests/
    ├── __init__.py
    ├── test_file_validator.py
    ├── test_exif_sanitizer.py
    ├── test_path_guard.py
    └── test_audit_logger.py
```

## Ordine di implementazione consigliato

1. `agents/security/` — tutti e 4 gli agenti
2. `core/orchestrator.py` — scheletro con dependency injection
3. `agents/analysis/` — Scanner e DateAnalyzer prima (riciclano codice esistente)
4. `agents/processing/` — EventMatcher e FolderManager prima (riciclano codice esistente)
5. `agents/processing/yearly_best_collector.py` — YearlyBestCollector
6. `agents/output/` — CheckpointManager e UIAgent
7. `tests/` — test agenti security
8. `main.py` — aggiorna entry point

## Dipendenze da aggiungere a requirements.txt

```
Pillow>=10.0.0          # già presente
imagehash>=4.3.1        # perceptual hashing per duplicati
python-dotenv>=1.0.0    # gestione credenziali da .env
piexif>=1.1.3           # stripping metadati GPS e XMP
bcrypt>=4.0.0           # hashing PIN sicuro (sostituisce SHA-256)
keyring>=25.0.0         # OS Keychain (Windows/macOS/Linux)
send2trash>=1.8.2       # cestino reversibile (invece di os.remove)
pip-audit>=2.7.0        # CVE scanning dipendenze
pip-tools>=7.0.0        # genera requirements.txt con hash
pytest>=8.0.0           # test
```

> Le dipendenze AI (CLIP, transformers) sono opzionali e gestite con try/import
> nel SmartClassifierAgent — se non presenti, l'agente usa un fallback basato
> sul nome file e sulla data.
