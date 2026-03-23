"""
AnomalyDetectorAgent — Fase 2, step 7
Monitora il log degli eventi per pattern anomali e avvisa l'utente.
Non blocca le operazioni: serve solo per allerta.
"""
import time
import logging
from collections import deque
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AnomalyDetectorAgent:
    """
    Monitora il log degli eventi per pattern anomali e avvisa l'utente.
    Non blocca le operazioni: serve solo per allerta.

    Anomalie rilevate:
    - Troppe delete in poco tempo (possibile errore utente)
    - Tentativi ripetuti di path traversal
    - Tentativi ripetuti di autenticazione fallita
    """

    # Soglie configurabili
    MAX_DELETES_PER_WINDOW = 20     # max 20 delete in DELETE_WINDOW secondi
    DELETE_WINDOW_SECONDS = 120     # finestra temporale 2 minuti
    MAX_TRAVERSAL_ATTEMPTS = 3      # max 3 tentativi di traversal

    def __init__(self, alert_callback: Optional[Callable[[str, str], None]] = None):
        """
        alert_callback: funzione(tipo_anomalia, messaggio) chiamata quando
                        viene rilevata un'anomalia. Tipicamente mostra un
                        toast nella GUI.
        """
        if alert_callback is None:
            def _default_alert(tipo, msg):
                logger.warning("ANOMALIA [%s]: %s", tipo, msg)
            self.alert_callback = _default_alert
        else:
            self.alert_callback = alert_callback

        self._delete_timestamps: deque = deque()
        self._traversal_count: int = 0
        self._mass_delete_alerted: bool = False

    def on_delete(self, path: str):
        """Chiama ogni volta che viene eliminato un file."""
        now = time.time()
        self._delete_timestamps.append(now)

        # Rimuovi delete più vecchie della finestra temporale
        while self._delete_timestamps and \
              (now - self._delete_timestamps[0]) > self.DELETE_WINDOW_SECONDS:
            self._delete_timestamps.popleft()
            self._mass_delete_alerted = False  # Reset alert quando finestra scade

        if len(self._delete_timestamps) >= self.MAX_DELETES_PER_WINDOW and not self._mass_delete_alerted:
            self._mass_delete_alerted = True
            self.alert_callback(
                'MASS_DELETE',
                f"{len(self._delete_timestamps)} file eliminati in "
                f"{self.DELETE_WINDOW_SECONDS // 60} minuti. "
                f"Controlla che non sia un errore."
            )

    def on_traversal_attempt(self, attempted_path: str):
        """Chiama ogni volta che PathGuard blocca un path traversal."""
        self._traversal_count += 1
        if self._traversal_count >= self.MAX_TRAVERSAL_ATTEMPTS:
            self.alert_callback(
                'PATH_TRAVERSAL',
                f"{self._traversal_count} tentativi di accesso a path non "
                f"autorizzati. Ultimo: {str(attempted_path)[:50]}"
            )

    def on_auth_failure(self, attempt_number: int):
        """Chiama ad ogni PIN errato."""
        if attempt_number >= 2:
            self.alert_callback(
                'AUTH_FAILURE',
                f"Tentativo {attempt_number}/3 di accesso con PIN errato."
            )

    def reset(self):
        """Resetta tutti i contatori (es. dopo login riuscito)."""
        self._delete_timestamps.clear()
        self._traversal_count = 0
        self._mass_delete_alerted = False
