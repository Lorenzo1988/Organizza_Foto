"""
EventMatcherAgent — Fase 4, step 26
Wrappa la logica di core/event_manager.py e folder_manager.py:determine_folder().
"""
import logging

logger = logging.getLogger(__name__)


class EventMatcherAgent:
    """
    Determina l'evento associato a una foto in base alla sua data.
    Wrappa EventManager e FolderManager.determine_folder().
    Imposta meta.event_name e meta.event_priority.
    """

    def __init__(self, event_manager, easter_dates: dict):
        self.event_manager = event_manager
        self.easter_dates = easter_dates
        # Importa qui per evitare import circolari
        from core.folder_manager import FolderManager

    def match(self, meta):
        """
        Determina la cartella evento per la foto.
        Ritorna meta con event_name e event_priority aggiornati.
        """
        if meta.date is None:
            meta.event_name = None
            meta.event_priority = 0
            return meta

        try:
            folder_name, priority = self._determine_folder(meta.date)
            meta.event_name = folder_name
            meta.event_priority = priority
        except Exception as e:
            logger.debug("EventMatcher error su %s: %s", meta.current_path, e)
            meta.event_name = None
            meta.event_priority = 0

        return meta

    def _determine_folder(self, photo_date):
        """
        Determina il nome cartella e la priorità in base alla data.
        Ricicla la logica di core/folder_manager.py:determine_folder().
        """
        from config import MONTH_NAMES
        year = photo_date.year
        events = self.event_manager.events

        # Priority 5: Eventi puntuali
        for event_year, month, day, event_name in events['one_time']:
            if (photo_date.year == event_year and
                    photo_date.month == month and
                    photo_date.day == day):
                return (f"{year}_{event_name}", 5)

        # Priority 4: Pasqua
        if year in self.easter_dates:
            easter, easter_monday = self.easter_dates[year]
            if (photo_date.date() == easter.date() or
                    photo_date.date() == easter_monday.date()):
                return (f"{year}_Pasqua", 4)

        # Priority 3: Vacanze Natale
        if ((photo_date.month == 12 and photo_date.day >= 20) or
                (photo_date.month == 1 and photo_date.day <= 6)):
            natale_year = year if photo_date.month == 12 else year - 1
            return (f"{natale_year}_Vacanze_Natale", 3)

        # Priority 2: Estate
        if photo_date.month in [7, 8]:
            return (f"{year}_Estate", 2)

        # Priority 6: Compleanni
        closest_birthday = self.event_manager.find_closest_birthday(photo_date)
        if closest_birthday:
            return (f"{year}_{closest_birthday}", 6)

        # Default: mese normale
        month_name = MONTH_NAMES.get(photo_date.month, f"{photo_date.month:02d}_Mese")
        return (f"{year}_{month_name}", 0)
