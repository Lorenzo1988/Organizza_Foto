# SUPPLY_CHAIN.md — Sicurezza della Supply Chain

Leggi questo file dopo SECURITY_AUDIT.md.
Implementa queste misure PRIMA di distribuire o usare il progetto su una nuova macchina.

Fonti: PEP 708, xygeni.io, artefact.com, caso PyTorch 2022, OpenSSF pip-audit.

---

## Il rischio concreto

Il `requirements.txt` attuale contiene:
```
Pillow>=10.0.0
```

Questo è vulnerabile in due modi:

**Typosquatting**: un pacchetto malevolo con nome simile (es. `Pi1low`) potrebbe
essere installato per errore di battitura.

**Dependency confusion**: l'attacco che ha colpito PyTorch nel 2022. Un attaccante
pubblica su PyPI un pacchetto con lo stesso nome di una dipendenza interna/privata,
con numero di versione più alto. pip lo installa al posto di quello legittimo,
eseguendo codice arbitrario.

**Versioni vulnerabili**: `>=10.0.0` permette l'installazione di qualsiasi
versione futura, anche se contiene CVE critici scoperti dopo.

---

## Soluzione 1 — requirements.txt con hash (obbligatorio)

### Genera il file con hash

```bash
# Installa pip-tools
pip install pip-tools

# Crea requirements.in con le dipendenze dirette (senza vincoli di versione stretti)
cat > requirements.in << 'EOF'
Pillow>=10.0.0
imagehash>=4.3.1
python-dotenv>=1.0.0
piexif>=1.1.3
send2trash>=1.8.2
keyring>=25.0.0
bcrypt>=4.0.0
pytest>=8.0.0
pip-audit>=2.7.0
EOF

# Genera requirements.txt con versioni pinnate e hash SHA-256
pip-compile --generate-hashes requirements.in
```

Il risultato sarà simile a:
```
Pillow==10.4.0 \
    --hash=sha256:a9c3... \
    --hash=sha256:b2f1...
```

### Installa verificando gli hash

```bash
pip install -r requirements.txt --require-hashes
```

Il flag `--require-hashes` fa fallire l'installazione se l'hash non corrisponde,
anche se la versione è quella giusta. Protegge da pacchetti manomessi in transit.

---

## Soluzione 2 — DependencyAuditAgent (nuovo agente)

**File**: `agents/security/dependency_audit.py`

```python
import subprocess
import json
import os
import time
from pathlib import Path

class DependencyAuditAgent:
    """
    Esegue pip-audit per trovare CVE nelle dipendenze installate.
    Viene chiamato all'avvio dell'app (max una volta ogni 7 giorni).
    Non blocca l'app se trova vulnerabilità — avvisa e logga.
    """

    AUDIT_CACHE_FILE = '.last_audit'
    AUDIT_INTERVAL_DAYS = 7

    def __init__(self, app_dir: str, audit_logger=None):
        self.app_dir = Path(app_dir)
        self.cache_path = self.app_dir / self.AUDIT_CACHE_FILE
        self.audit_logger = audit_logger

    def should_run(self) -> bool:
        """Ritorna True se è passata più di una settimana dall'ultimo audit."""
        if not self.cache_path.exists():
            return True
        try:
            last_run = float(self.cache_path.read_text())
            days_elapsed = (time.time() - last_run) / 86400
            return days_elapsed >= self.AUDIT_INTERVAL_DAYS
        except Exception:
            return True

    def run(self) -> list[dict]:
        """
        Esegue pip-audit e ritorna lista di vulnerabilità trovate.
        Ritorna [] se pip-audit non è installato o se tutto è OK.
        """
        if not self.should_run():
            return []

        try:
            result = subprocess.run(
                ['pip-audit', '--format=json', '--progress-spinner=off'],
                capture_output=True, text=True, timeout=60
            )
            self.cache_path.write_text(str(time.time()))

            if result.returncode == 0:
                return []  # Nessuna vulnerabilità

            vulns = json.loads(result.stdout)
            vulnerabilities = []
            for dep in vulns.get('dependencies', []):
                for vuln in dep.get('vulns', []):
                    vulnerabilities.append({
                        'package': dep['name'],
                        'version': dep['version'],
                        'cve': vuln['id'],
                        'description': vuln.get('description', '')[:200],
                        'fix_versions': vuln.get('fix_versions', []),
                    })

            if self.audit_logger and vulnerabilities:
                for v in vulnerabilities:
                    self.audit_logger.log_event(
                        'CVE_FOUND',
                        f"{v['package']}=={v['version']} {v['cve']}"
                    )

            return vulnerabilities

        except FileNotFoundError:
            # pip-audit non installato: avvisa ma non blocca
            return []
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []

    def format_warning(self, vulnerabilities: list[dict]) -> str:
        """Formatta le vulnerabilità per la UI."""
        if not vulnerabilities:
            return ''
        lines = [f"⚠️  {len(vulnerabilities)} vulnerabilità nelle dipendenze:"]
        for v in vulnerabilities[:5]:  # Mostra max 5
            fix = f" → aggiorna a {v['fix_versions'][0]}" if v['fix_versions'] else ''
            lines.append(f"  • {v['package']}=={v['version']}: {v['cve']}{fix}")
        if len(vulnerabilities) > 5:
            lines.append(f"  ... e altre {len(vulnerabilities) - 5}")
        lines.append("Esegui: pip install -r requirements.txt per aggiornare")
        return '\n'.join(lines)
```

### Integrazione in main.py

```python
# All'avvio, dopo CredentialGuardAgent e prima della GUI
dep_audit = DependencyAuditAgent(app_dir=os.path.dirname(__file__))
vulns = dep_audit.run()
if vulns:
    warning_msg = dep_audit.format_warning(vulns)
    print(warning_msg)
    # In GUI: mostra un banner arancione non bloccante nella status bar
```

---

## Soluzione 3 — .gitignore aggiornato

Aggiungi al `.gitignore`:

```gitignore
# Supply chain
requirements.txt.bak
pip-audit-report.json
.last_audit

# Ambienti virtuali (mai committare)
venv/
.venv/
env/
.env/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Sicurezza
.env
.env.local
.auth_hash
audit_log.txt
audit_log*.txt
report_*.html
progress_checkpoint.txt
```

---

## requirements.txt finale (esempio con hash)

```
# Generato con: pip-compile --generate-hashes requirements.in
# Installa con: pip install -r requirements.txt --require-hashes

bcrypt==4.2.1 \
    --hash=sha256:... \
    --hash=sha256:...
imagehash==4.3.1 \
    --hash=sha256:... \
    --hash=sha256:...
keyring==25.7.0 \
    --hash=sha256:... \
    --hash=sha256:...
piexif==1.1.3 \
    --hash=sha256:... \
    --hash=sha256:...
Pillow==11.2.1 \
    --hash=sha256:... \
    --hash=sha256:...
pip-audit==2.8.0 \
    --hash=sha256:... \
    --hash=sha256:...
python-dotenv==1.0.1 \
    --hash=sha256:... \
    --hash=sha256:...
send2trash==1.8.3 \
    --hash=sha256:... \
    --hash=sha256:...
pytest==8.3.5 \
    --hash=sha256:... \
    --hash=sha256:...
```

Nota: gli hash reali vengono generati da `pip-compile --generate-hashes`.
Non inserire hash inventati — pip li verificherà e fallirà.

---

## Test da aggiungere

**File**: `tests/test_dependency_audit.py`

```python
def test_audit_runs_when_cache_missing():
    # Rimuovi .last_audit → should_run() = True

def test_audit_skipped_within_7_days():
    # Crea .last_audit con timestamp recente → should_run() = False

def test_audit_graceful_if_pip_audit_missing():
    # Simula FileNotFoundError → run() ritorna []
```
