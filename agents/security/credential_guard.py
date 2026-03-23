"""
CredentialGuardAgent — Fase 2, step 8
Verifica che nessuna credenziale sia hardcoded nel codice e che le
variabili d'ambiente necessarie siano state caricate dal file .env.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS = [
    r'api[_-]?key\s*=\s*["\'][^"\']{8,}',
    r'password\s*=\s*["\'][^"\']+',
    r'secret\s*=\s*["\'][^"\']{8,}',
    r'token\s*=\s*["\'][^"\']{8,}',
    r'client[_-]?id\s*=\s*["\'][^"\']{8,}',
]


class CredentialGuardAgent:
    """
    Verifica all'avvio che nessuna credenziale sia hardcoded nel codice.
    Controlla anche che SOURCE_FOLDER e DESTINATION_FOLDER siano stati
    caricati da .env e non siano vuoti.

    Deve essere la PRIMA cosa chiamata in main.py.
    """

    def check_config(self, config_path: str) -> List[str]:
        """
        Scansiona config.py cercando pattern di credenziali hardcoded.
        Ritorna lista di warning (vuota se tutto ok).
        """
        warnings_list = []
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, content):
                    warnings_list.append(
                        f"Possibile credenziale hardcoded: pattern '{pattern}'"
                    )
        except FileNotFoundError:
            warnings_list.append(f"File config non trovato: {config_path}")
        except Exception as e:
            logger.warning("CredentialGuard: errore lettura config: %s", e)
        return warnings_list

    def check_env_loaded(self, source: str, destination: str) -> List[str]:
        """Verifica che i percorsi obbligatori siano stati caricati."""
        errors = []
        if not source:
            errors.append("SOURCE_FOLDER non impostato. Controlla il file .env")
        if not destination:
            errors.append("DESTINATION_FOLDER non impostato. Controlla il file .env")
        return errors

    def verify_folder_access(self, path: str, path_guard=None) -> tuple:
        """
        Verifica che la cartella esista e sia accessibile.
        Ritorna (True, '') o (False, messaggio_errore).
        """
        import os
        if not path:
            return False, "Percorso vuoto"
        if not os.path.exists(path):
            return False, f"Cartella non trovata: {path}"
        if not os.access(path, os.R_OK):
            return False, f"Permesso di lettura negato: {path}"
        if path_guard is not None and not path_guard.is_safe_path(path):
            return False, f"Path non autorizzato: {path}"
        return True, ''
