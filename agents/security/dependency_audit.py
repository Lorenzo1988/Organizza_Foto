"""
DependencyAuditAgent — Fase 2, step 12
Esegue pip-audit per trovare CVE nelle dipendenze installate.
Viene chiamato all'avvio dell'app (max una volta ogni 7 giorni).
Non blocca l'app se trova vulnerabilità — avvisa e logga.
"""
import subprocess
import json
import logging
import time
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


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

    def run(self) -> List[Dict]:
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

            try:
                vulns_json = json.loads(result.stdout)
            except json.JSONDecodeError:
                # pip-audit può avere output diverso in alcune versioni
                return []

            vulnerabilities = []
            for dep in vulns_json.get('dependencies', []):
                for vuln in dep.get('vulns', []):
                    vulnerabilities.append({
                        'package': dep['name'],
                        'version': dep.get('version', '?'),
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
            logger.debug("pip-audit non installato: audit saltato")
            return []
        except subprocess.TimeoutExpired:
            logger.debug("pip-audit timeout")
            return []
        except Exception as e:
            logger.debug("DependencyAudit: errore: %s", e)
            return []

    def format_warning(self, vulnerabilities: List[Dict]) -> str:
        """Formatta le vulnerabilità per la UI."""
        if not vulnerabilities:
            return ''
        lines = [f"⚠️  {len(vulnerabilities)} vulnerabilità nelle dipendenze:"]
        for v in vulnerabilities[:5]:
            fix = f" → aggiorna a {v['fix_versions'][0]}" if v['fix_versions'] else ''
            lines.append(f"  • {v['package']}=={v['version']}: {v['cve']}{fix}")
        if len(vulnerabilities) > 5:
            lines.append(f"  ... e altre {len(vulnerabilities) - 5}")
        lines.append("Esegui: pip install -r requirements.txt per aggiornare")
        return '\n'.join(lines)
