"""
PathGuardAgent — Fase 2, step 5
Previene path traversal e sandbox escape.
Tutti i path dinamici devono passare per safe_join().
"""
import re
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Pattern per nomi highlight validi: alfanumerici, spazio, underscore, trattino, accenti
VALID_HIGHLIGHT_NAME_RE = re.compile(
    r'^[\w\s\-àáâãäåèéêëìíîïòóôõöùúûüýÿÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÝ]+$',
    re.UNICODE
)
MAX_HIGHLIGHT_NAME_LENGTH = 100


class PathGuardAgent:
    """
    Agente di sicurezza per i path del filesystem.
    - Previene path traversal (../../etc/passwd)
    - Mantiene una sandbox di cartelle consentite
    - Valida i nomi inseriti dall'utente

    PathGuard è l'UNICO agente che DEVE lanciare ValueError —
    il suo errore ferma immediatamente l'operazione.
    """

    def __init__(self, allowed_roots: List[str]):
        self._allowed_roots: List[Path] = []
        for root in allowed_roots:
            if root:
                try:
                    resolved = Path(root).resolve()
                    self._allowed_roots.append(resolved)
                except Exception as e:
                    logger.warning("PathGuard: impossibile risolvere root %s: %s", root, e)

    def add_allowed_root(self, path: str):
        """Aggiunge una radice consentita alla sandbox."""
        if path:
            try:
                resolved = Path(path).resolve()
                if resolved not in self._allowed_roots:
                    self._allowed_roots.append(resolved)
            except Exception as e:
                logger.warning("PathGuard: impossibile aggiungere root %s: %s", path, e)

    def is_safe_path(self, path: str) -> bool:
        """
        Verifica che il path sia dentro una delle radici consentite.
        Ritorna True se sicuro, False altrimenti.
        """
        if not path:
            return False
        try:
            resolved = Path(path).resolve()
            for root in self._allowed_roots:
                try:
                    resolved.relative_to(root)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def safe_join(self, base: str, *parts: str) -> str:
        """
        Unisce i path in modo sicuro.
        Lancia ValueError se il risultato esce dalla sandbox o contiene traversal.
        """
        if not base:
            raise ValueError("PathGuard: base path vuoto")

        # Costruisci il path risultante
        try:
            result = Path(base)
            for part in parts:
                if not part:
                    continue
                # Controllo rapido per tentativi espliciti di traversal
                if '..' in Path(part).parts:
                    anomaly_hint = str(part)
                    raise ValueError(
                        f"PathGuard: tentativo di path traversal bloccato: '{anomaly_hint}'"
                    )
                result = result / part
            resolved = result.resolve()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"PathGuard: errore nella costruzione del path: {e}") from e

        # Verifica sandbox
        if not self._is_within_allowed(resolved):
            raise ValueError(
                f"PathGuard: path '{resolved}' fuori dalla sandbox consentita"
            )

        return str(resolved)

    def validate_highlight_name(self, name: str) -> str:
        """
        Valida e sanitizza un nome highlight inserito dall'utente.
        Lancia ValueError se il nome non è valido.
        Ritorna il nome pulito (strip).
        """
        if not name:
            raise ValueError("Il nome dell'highlight non può essere vuoto")

        clean = name.strip()

        if not clean:
            raise ValueError("Il nome dell'highlight non può essere vuoto")

        if len(clean) > MAX_HIGHLIGHT_NAME_LENGTH:
            raise ValueError(
                f"Nome troppo lungo ({len(clean)} caratteri, max {MAX_HIGHLIGHT_NAME_LENGTH})"
            )

        # Blocca path traversal esplicito
        if '..' in clean or '/' in clean or '\\' in clean:
            raise ValueError(f"Nome highlight contiene caratteri non consentiti: '{clean}'")

        if not VALID_HIGHLIGHT_NAME_RE.match(clean):
            raise ValueError(
                f"Nome highlight contiene caratteri non consentiti: '{clean}'. "
                "Usa solo lettere, numeri, spazi, trattini e underscore."
            )

        return clean

    # ── Internals ─────────────────────────────────────────────────

    def _is_within_allowed(self, resolved: Path) -> bool:
        """Verifica che il path risolto sia dentro almeno una radice consentita."""
        if not self._allowed_roots:
            # Nessuna radice configurata: permissivo (per test)
            return True
        for root in self._allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False
