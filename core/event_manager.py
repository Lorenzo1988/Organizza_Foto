import os
from datetime import datetime
from config import EVENTS_FILE, BIRTHDAY_THRESHOLD_DAYS


class EventManager:
    """Gestisce il caricamento e la ricerca di eventi"""

    def __init__(self):
        self.events = self.load_events()

    def load_events(self):
        """Carica gli eventi dal file esterno"""
        events = {
            'recurring': [],
            'one_time': []
        }

        if not os.path.exists(EVENTS_FILE):
            print(f"⚠️  File eventi non trovato: {EVENTS_FILE}")
            print("   Creo un file di esempio...")
            self._create_example_file()
            print(f"✓ Creato {EVENTS_FILE} con esempi\n")

        try:
            with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    if not line or line.startswith('#'):
                        continue

                    parts = [p.strip() for p in line.split('-')]
                    if len(parts) != 3:
                        print(f"⚠️  Riga {line_num} ignorata (formato errato): {line}")
                        continue

                    event_type, event_name, date_str = parts
                    date_str = date_str.replace(' ', '')

                    # Eventi ricorrenti (4 cifre: MMDD)
                    if len(date_str) == 4:
                        try:
                            month = int(date_str[:2])
                            day = int(date_str[2:])
                            events['recurring'].append((month, day, event_name))
                        except ValueError:
                            print(f"⚠️  Riga {line_num} ignorata (data invalida): {line}")

                    # Eventi puntuali (8 cifre: YYYYMMDD)
                    elif len(date_str) == 8:
                        try:
                            year = int(date_str[:4])
                            month = int(date_str[4:6])
                            day = int(date_str[6:8])
                            events['one_time'].append((year, month, day, event_name))
                        except ValueError:
                            print(f"⚠️  Riga {line_num} ignorata (data invalida): {line}")

        except Exception as e:
            print(f"❌ Errore nella lettura di {EVENTS_FILE}: {e}")

        return events

    def _create_example_file(self):
        """Crea un file di esempio"""
        with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
            f.write("# File eventi - formato:\n")
            f.write("# Tipo - Nome_Cartella - Data\n")
            f.write("# Per eventi ricorrenti (compleanni): MMDD\n")
            f.write("# Per eventi puntuali (matrimoni): YYYYMMDD\n\n")
            f.write("Compleanno - Compleanno_Gemelli - 0329\n")
            f.write("Compleanno - Compleanno_Mamma - 0210\n")
            f.write("Compleanno - Compleanno_Papa - 0115\n")
            f.write("# Matrimonio - Matrimonio_Mario_e_Laura - 20250615\n")

    def find_closest_birthday(self, photo_date):
        """Trova il compleanno più vicino alla data della foto"""
        year = photo_date.year
        min_distance = float('inf')
        closest_event = None

        for month, day, event_name in self.events['recurring']:
            for year_offset in [-1, 0, 1]:
                try:
                    event_date = datetime(year + year_offset, month, day)
                    distance = abs((photo_date - event_date).days)

                    if distance <= BIRTHDAY_THRESHOLD_DAYS and distance < min_distance:
                        min_distance = distance
                        closest_event = event_name
                except:
                    pass

        return closest_event