# PRIVACY_SECURITY.md — Gestione Credenziali e Privacy

Leggi questo file DOPO SECURITY.md e PRIMA di implementare ExportAgent e ExifSanitizerAgent.

---

## Problema 1 — Credenziali in chiaro

### Situazione attuale (rischio)

`config.py` è già committato su GitHub con percorsi personali in chiaro:

```python
# RISCHIO: percorso personale esposto pubblicamente
SOURCE_FOLDER = r"C:\Users\loren\OneDrive\Desktop\Archivio_Foto\..."
```

Se in futuro si aggiungono API key per cloud (Google Photos, OneDrive, Dropbox),
andrebbero nello stesso file — e finirebbero in Git.

### Soluzione: file .env + python-dotenv

**Regola assoluta**: nessuna credenziale, API key o percorso personale
va mai in `config.py` o in qualsiasi file committato.

#### 1. Crea `.env` (mai committato)

```bash
# .env  ← nella root del progetto, NON in Git
SOURCE_FOLDER=C:\Users\loren\OneDrive\Desktop\Archivio_Foto\sorgente
DESTINATION_FOLDER=C:\Users\loren\OneDrive\Desktop\Archivio_Foto\organizzato

# Credenziali cloud (opzionali, solo se usi ExportAgent)
GOOGLE_PHOTOS_API_KEY=
ONEDRIVE_CLIENT_ID=
ONEDRIVE_CLIENT_SECRET=
DROPBOX_ACCESS_TOKEN=
```

#### 2. Aggiungi `.env` al `.gitignore`

```bash
# .gitignore
.env
.env.local
*.env
progress_checkpoint.txt
audit_log.txt
__pycache__/
*.pyc
```

#### 3. Aggiorna `config.py` per leggere da `.env`

Sostituisci le prime righe di `config.py` con:

```python
import os
from dotenv import load_dotenv

load_dotenv()  # carica .env se presente

# Percorsi — letti da .env, con fallback a stringa vuota
SOURCE_FOLDER = os.getenv('SOURCE_FOLDER', '')
DESTINATION_FOLDER = os.getenv('DESTINATION_FOLDER', '')

# Credenziali cloud — MAI hardcoded
GOOGLE_PHOTOS_API_KEY = os.getenv('GOOGLE_PHOTOS_API_KEY', '')
ONEDRIVE_CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_CLIENT_SECRET = os.getenv('ONEDRIVE_CLIENT_SECRET', '')
DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN', '')

# ... resto del config invariato ...
```

#### 4. Aggiungi `python-dotenv` a requirements.txt

```
python-dotenv>=1.0.0
```

#### 5. Crea `.env.example` (questo SÌ si committa)

```bash
# .env.example  ← template pubblico senza valori reali
SOURCE_FOLDER=C:\percorso\alla\cartella\sorgente
DESTINATION_FOLDER=C:\percorso\alla\cartella\destinazione

# Credenziali cloud (opzionali)
GOOGLE_PHOTOS_API_KEY=
ONEDRIVE_CLIENT_ID=
ONEDRIVE_CLIENT_SECRET=
DROPBOX_ACCESS_TOKEN=
```

### CredentialGuardAgent

Aggiungi questo controllo all'avvio dell'Orchestratore:

```python
# agents/security/credential_guard.py

class CredentialGuardAgent:
    """
    Verifica all'avvio che nessuna credenziale sia hardcoded nel codice.
    Controlla anche che SOURCE_FOLDER e DESTINATION_FOLDER siano stati
    caricati da .env e non siano vuoti.
    """

    DANGEROUS_PATTERNS = [
        r'api[_-]?key\s*=\s*["\'][^"\']{8,}',
        r'password\s*=\s*["\'][^"\']+',
        r'secret\s*=\s*["\'][^"\']{8,}',
        r'token\s*=\s*["\'][^"\']{8,}',
        r'client[_-]?id\s*=\s*["\'][^"\']{8,}',
    ]

    def check_config(self, config_path: str) -> list[str]:
        """
        Scansiona config.py cercando pattern di credenziali hardcoded.
        Ritorna lista di warning (vuota se tutto ok).
        """
        import re
        warnings = []
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, content):
                    warnings.append(f"Possibile credenziale hardcoded: pattern '{pattern}'")
        except Exception:
            pass
        return warnings

    def check_env_loaded(self, source: str, destination: str) -> list[str]:
        """Verifica che i percorsi obbligatori siano stati caricati."""
        errors = []
        if not source:
            errors.append("SOURCE_FOLDER non impostato. Controlla il file .env")
        if not destination:
            errors.append("DESTINATION_FOLDER non impostato. Controlla il file .env")
        return errors
```

Chiama `CredentialGuardAgent` come **primissima cosa** in `main.py`,
prima ancora di istanziare gli altri agenti. Se ritorna errori, blocca l'esecuzione.

---

## Problema 2 — Metadati GPS nelle foto condivise

### Il rischio concreto

Le foto scattate con smartphone contengono coordinate GPS precise nei metadati EXIF.
Quando una foto viene copiata in `📅 MIGLIORI_ANNO/` o condivisa via cloud
(OneDrive è già nella destination path del progetto!), porta con sé queste coordinate.

Una foto scattata a casa rivela l'indirizzo di casa.
Una foto scattata al lavoro rivela il luogo di lavoro.

### GpsStripperAgent

```python
# agents/security/gps_stripper.py

class GpsStripperAgent:
    """
    Rimuove i dati GPS dai metadati EXIF prima di copiare una foto
    in cartelle destinate alla condivisione pubblica o al cloud.
    """

    # Cartelle considerate "pubbliche" o a rischio condivisione
    PUBLIC_FOLDER_NAMES = {
        '📅 MIGLIORI_ANNO',
        '⭐ HIGHLIGHTS',
        '🖨️ DA_STAMPARE',
    }

    def __init__(self, strip_always: bool = False):
        """
        strip_always: se True, rimuove GPS da TUTTE le foto (non solo quelle pubbliche).
        Default False: rimuove solo nelle cartelle a rischio.
        """
        self.strip_always = strip_always

    def should_strip(self, destination_path: str) -> bool:
        """Determina se rimuovere GPS in base alla cartella di destinazione."""
        if self.strip_always:
            return True
        from pathlib import Path
        parts = Path(destination_path).parts
        return any(folder in parts for folder in self.PUBLIC_FOLDER_NAMES)

    def strip_gps(self, source_path: str, dest_path: str) -> bool:
        """
        Copia il file rimuovendo i dati GPS.
        Ritorna True se GPS rimosso, False se non c'era GPS o operazione fallita.
        """
        try:
            import piexif
            exif_dict = piexif.load(source_path)

            had_gps = bool(exif_dict.get('GPS'))
            if 'GPS' in exif_dict:
                exif_dict['GPS'] = {}  # svuota il blocco GPS

            exif_bytes = piexif.dump(exif_dict)

            from PIL import Image
            import shutil

            try:
                img = Image.open(source_path)
                img.save(dest_path, exif=exif_bytes)
                return had_gps
            except Exception:
                # Fallback: copia senza modifiche se PIL non riesce
                shutil.copy2(source_path, dest_path)
                return False

        except ImportError:
            # piexif non installato: copia senza stripping
            import shutil
            shutil.copy2(source_path, dest_path)
            return False
        except Exception:
            import shutil
            shutil.copy2(source_path, dest_path)
            return False

    def strip_gps_inplace(self, file_path: str) -> bool:
        """Rimuove GPS dal file in-place (sovrascrive il file originale)."""
        import tempfile, os, shutil
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
            tmp_path = tmp.name
        try:
            result = self.strip_gps(file_path, tmp_path)
            if result:
                shutil.move(tmp_path, file_path)
            else:
                os.remove(tmp_path)
            return result
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return False
```

### Dove integrare GpsStripperAgent

**1. In YearlyBestCollectorAgent** (obbligatorio):

```python
# agents/processing/yearly_best_collector.py

def collect(self, destination: str) -> dict:
    ...
    for photo_path in top_photos:
        dest = path_guard.safe_join(year_folder, os.path.basename(photo_path))
        audit_logger.log_copy(photo_path, dest)
        # Rimuovi GPS prima di copiare nella raccolta annuale
        self.gps_stripper.strip_gps(photo_path, dest)
    ...
```

**2. In ExportAgent** (obbligatorio):

```python
# Prima di qualsiasi copia verso cloud o cartelle condivise,
# passa sempre per gps_stripper.strip_gps(src, dst)
```

**3. In FolderManagerAgent per HIGHLIGHTS** (consigliato):

```python
# Quando si copia in ⭐ HIGHLIGHTS, stripping GPS opzionale
# (configurabile con STRIP_GPS_FROM_HIGHLIGHTS = True in .env)
```

### Dipendenza da aggiungere a requirements.txt

```
piexif>=1.1.3    # per stripping GPS
```

> Se `piexif` non è installato, `GpsStripperAgent` fa un fallback silenzioso
> copiando il file senza modifiche (comportamento safe-by-default).

---

## Riepilogo: nuovi agenti di sicurezza da aggiungere

| Agente | File | Quando si attiva |
|---|---|---|
| `CredentialGuardAgent` | `agents/security/credential_guard.py` | Avvio applicazione (prima di tutto) |
| `GpsStripperAgent` | `agents/security/gps_stripper.py` | Copia in HIGHLIGHTS, MIGLIORI_ANNO, export cloud |

## Aggiornamento .gitignore (obbligatorio)

Assicurati che questi file NON siano mai committati:

```gitignore
.env
.env.local
*.env
progress_checkpoint.txt
audit_log.txt
report_*.html
__pycache__/
*.pyc
*.pyo
.pytest_cache/
```

## Test aggiuntivi da scrivere

### test_credential_guard.py
- `test_detects_hardcoded_api_key()` — config con api_key hardcoded → warning
- `test_clean_config_passes()` — config pulito → nessun warning
- `test_missing_source_folder()` — SOURCE_FOLDER vuoto → errore

### test_gps_stripper.py
- `test_strips_gps_from_jpeg()` — JPEG con GPS → copia senza GPS
- `test_no_gps_no_error()` — JPEG senza GPS → copia normale, nessun crash
- `test_should_strip_highlights_folder()` — path in HIGHLIGHTS → True
- `test_should_not_strip_archive()` — path in ARCHIVIO → False
