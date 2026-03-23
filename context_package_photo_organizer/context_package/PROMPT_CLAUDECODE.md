# PROMPT_CLAUDECODE.md — Prompt da incollare in Claude Code

Copia e incolla questo testo come primo messaggio quando avvii Claude Code
nella cartella del progetto.

---

## Prompt

```
Leggi in ordine tutti questi file prima di scrivere qualsiasi codice:
1.  AGENTS.md
2.  ARCHITECTURE.md
3.  SECURITY.md
4.  SECURITY_AUDIT.md
5.  AUTHENTICATION_V2.md   ← usa questo, NON AUTHENTICATION.md
6.  PIL_HARDENING.md
7.  SUPPLY_CHAIN.md
8.  MONITORING.md
9.  PRIVACY_SECURITY.md
10. AGENTS_SPEC.md
11. MIGRATION.md
12. UI_DESIGN.md

Poi implementa il progetto in questo ordine esatto:

── FASE 1: Configurazione PIL (prima di TUTTO) ────────────────────
0. main.py — prima riga eseguibile:
   - Image.MAX_IMAGE_PIXELS = 100_000_000
   - warnings.filterwarnings('error', category=Image.DecompressionBombWarning)

── FASE 2: Security Gate ──────────────────────────────────────────
1.  agents/security/decompression_bomb_guard.py  (DecompressionBombGuardAgent)
2.  agents/security/memory_manager.py            (MemoryManagerAgent)
3.  agents/security/file_validator.py            (FileValidatorAgent)
4.  agents/security/exif_sanitizer.py            (ExifSanitizerAgent — usa getexif() NON _getexif())
5.  agents/security/path_guard.py                (PathGuardAgent)
6.  agents/security/audit_logger.py              (AuditLoggerAgent v2 — JSON + RotatingFileHandler)
7.  agents/security/anomaly_detector.py          (AnomalyDetectorAgent)
8.  agents/security/credential_guard.py          (CredentialGuardAgent)
9.  agents/security/gps_stripper.py              (GpsStripperAgent)
10. agents/security/xmp_stripper.py              (XmpStripperAgent)
11. agents/security/auth_agent.py                (AuthenticationAgent v2 — bcrypt + keyring)
12. agents/security/dependency_audit.py          (DependencyAuditAgent)
13. tests/test_file_validator.py
14. tests/test_path_guard.py
15. tests/test_exif_sanitizer.py
16. tests/test_audit_logger.py
17. tests/test_auth_agent_v2.py
18. tests/test_pil_hardening.py
19. tests/test_monitoring.py
20. tests/test_dependency_audit.py
→ esegui: pytest tests/ -v  ← TUTTI devono passare prima di proseguire

── FASE 3: Core + Analisi ─────────────────────────────────────────
21. core/orchestrator.py                (Orchestratore + PhotoMetadata)
    → inietta AnomalyDetector in PathGuard per rilevare traversal
22. agents/analysis/scanner.py          (ScannerAgent)
23. agents/analysis/date_analyzer.py    (DateAnalyzerAgent)
24. agents/analysis/duplicate_detector.py
25. agents/analysis/smart_classifier.py (fallback senza AI: OK)

── FASE 4: Elaborazione ───────────────────────────────────────────
26. agents/processing/event_matcher.py
27. agents/processing/folder_manager.py
    → copy-verify-delete (NON shutil.move diretto)
    → ogni operazione: audit_logger prima, poi filesystem
    → ogni delete: send2trash (NON os.remove)
28. agents/processing/highlights_curator.py
29. agents/processing/yearly_best_collector.py
    → usa GpsStripperAgent + XmpStripperAgent prima di copiare

── FASE 5: Output ─────────────────────────────────────────────────
30. agents/output/checkpoint_manager.py  (valida ogni path con PathGuard)
31. agents/output/report_generator.py
32. agents/output/export_agent.py        (GPS + XMP stripping obbligatorio)

── FASE 6: UI ─────────────────────────────────────────────────────
33. ui/auth_dialogs.py
    → PinSetupDialog: PIN come bytearray (azzerabile)
    → LoginDialog: PIN come bytearray, shake animation su errore
    → LockScreenDialog: dopo timeout sessione
34. ui/components.py
    → PhotoProgressBar, ToastNotification (per anomalie), ActionButton
    → InfoBar con badge GPS/XMP rimosso, badge duplicati
    → StatusBar con contatori + indicatore sessione rimanente
35. agents/output/ui_agent.py
    → usa memory_manager.open_thumbnail() per OGNI Image.open()
    → MAI Image.open() diretto nella GUI
    → DependencyAuditAgent: mostra banner se CVE trovati
    → AnomalyDetector collegato al tasto delete e agli highlights

── FASE 7: Integrazione finale ────────────────────────────────────
36. main.py  (entry point completo — vedi schema in MIGRATION.md)
37. requirements.in  (dipendenze dirette senza versioni strette)
    → Poi genera: pip-compile --generate-hashes requirements.in
38. .env.example
39. .gitignore  (includi: .env, .auth_hash, .auth_hash_enc, .last_audit,
                  audit_log*.txt, report_*.html, progress_checkpoint.txt,
                  __pycache__/, *.pyc, venv/, .venv/)
40. Genera requirements.txt con hash:
    pip install pip-tools && pip-compile --generate-hashes requirements.in

── REGOLE ASSOLUTE (non negoziabili) ─────────────────────────────
PIL:
- Image.MAX_IMAGE_PIXELS configurato prima di qualsiasi Image.open()
- TUTTI i Image.open() passano per MemoryManagerAgent.open_thumbnail()
- ExifSanitizerAgent usa getexif() + get_ifd(0x8825), NON _getexif()

Sicurezza:
- TUTTI i path dinamici → PathGuardAgent.safe_join()
- OGNI operazione filesystem (move/copy/delete) → AuditLoggerAgent PRIMA
- OGNI delete → send2trash (non os.remove)
- PIN raccolto come bytearray, azzerato dopo uso
- AuthAgent usa bcrypt (cost 12) + keyring

Privacy:
- GpsStripperAgent + XmpStripperAgent in YearlyBestCollector e ExportAgent
- AuditLogger non scrive mai path assoluti (solo nome file + hash)

Supply chain:
- requirements.txt generato con --generate-hashes
- DependencyAuditAgent all'avvio (max 1 volta a settimana)

Codice:
- Nessun print(DEBUG) → logging.debug()
- Tutti i colori/font da THEME e FONTS in config.py
- CredentialGuardAgent come PRIMA cosa in main.py
- Nessun sheet hardcoded

NON modificare:
- config.py (solo aggiunte in fondo)
- file_eventi.txt
- utils/date_utils.py
- utils/file_utils.py (solo aggiornamento copy_file per MD5 check)
```
