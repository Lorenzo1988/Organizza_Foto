import os
import shutil
from datetime import datetime
from config import (
    MONTH_NAMES, HIGHLIGHTS_FOLDER_NAME, EVENTS_FOLDER_NAME,
    ARCHIVE_FOLDER_NAME, TO_PRINT_FOLDER_NAME
)
from utils.file_utils import copy_file_with_duplicate_handling


class FolderManager:
    """Gestisce l'organizzazione delle foto nelle cartelle"""

    def __init__(self, destination_folder, event_manager, easter_dates):
        self.destination_folder = destination_folder
        self.event_manager = event_manager
        self.easter_dates = easter_dates

        # Crea cartelle base
        self.highlights_folder = os.path.join(destination_folder, HIGHLIGHTS_FOLDER_NAME)
        self.events_folder = os.path.join(destination_folder, EVENTS_FOLDER_NAME)
        self.archive_folder = os.path.join(destination_folder, ARCHIVE_FOLDER_NAME)
        self.to_print_folder = os.path.join(destination_folder, TO_PRINT_FOLDER_NAME)

        for folder in [self.highlights_folder, self.events_folder, self.archive_folder, self.to_print_folder]:
            os.makedirs(folder, exist_ok=True)

    def determine_folder(self, photo_date):
        """
        Determina la cartella di destinazione in base alla data
        Restituisce: (folder_name, priority)
        """
        year = photo_date.year
        events = self.event_manager.events

        # Priority 5: Eventi puntuali (matrimoni, etc.)
        for event_year, month, day, event_name in events['one_time']:
            if photo_date.year == event_year and photo_date.month == month and photo_date.day == day:
                return (f"{year}_{event_name}", 5)

        # Priority 4: Pasqua
        if year in self.easter_dates:
            easter, easter_monday = self.easter_dates[year]
            if photo_date.date() == easter.date() or photo_date.date() == easter_monday.date():
                return (f"{year}_Pasqua", 4)

        # Priority 3: Vacanze Natale
        if (photo_date.month == 12 and photo_date.day >= 20) or \
                (photo_date.month == 1 and photo_date.day <= 6):
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

    def organize_to_default(self, photo_path, photo_date):
        """Sposta (NON copia) foto nella cartella predefinita (EVENTI o ARCHIVIO)"""
        folder_name, priority = self.determine_folder(photo_date)
        year = folder_name.split('_')[0]

        # Scegli tra EVENTI o ARCHIVIO
        if priority >= 3:
            base_folder = os.path.join(self.events_folder, year)
        else:
            base_folder = os.path.join(self.archive_folder, year)

        dest_folder = os.path.join(base_folder, folder_name)
        os.makedirs(dest_folder, exist_ok=True)

        filename = os.path.basename(photo_path)
        dest_path = os.path.join(dest_folder, filename)

        # Gestisci duplicati
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                new_filename = f"{base}_{counter}{ext}"
                dest_path = os.path.join(dest_folder, new_filename)
                counter += 1

        # SPOSTA (non copiare)
        shutil.move(photo_path, dest_path)
        return dest_path

    def add_to_print(self, photo_path, photo_date):
        """Aggiunge la foto alla cartella Da Stampare (organizzata per anno)"""
        year = photo_date.year
        year_folder = os.path.join(self.to_print_folder, str(year))

        # Copia in Da Stampare/Anno
        copy_file_with_duplicate_handling(photo_path, year_folder)

    def move_to_highlight(self, photo_path, photo_date, highlight_name, add_to_print=False):
        """Copia la foto in un highlight E assicura che sia anche in EVENTI/ARCHIVIO"""
        # Crea cartella highlight SENZA anno (solo il nome)
        highlight_path = os.path.join(self.highlights_folder, highlight_name)

        # Copia in highlight
        copy_file_with_duplicate_handling(photo_path, highlight_path)

        # Se richiesto, aggiungi anche a Da Stampare
        if add_to_print:
            self.add_to_print(photo_path, photo_date)

        # Determina dove DOVREBBE essere in EVENTI/ARCHIVIO
        folder_name, priority = self.determine_folder(photo_date)
        folder_year = folder_name.split('_')[0]

        if priority >= 3:
            base_folder = os.path.join(self.events_folder, folder_year)
        else:
            base_folder = os.path.join(self.archive_folder, folder_year)

        dest_folder = os.path.join(base_folder, folder_name)

        # Se la foto NON è nella cartella corretta di EVENTI/ARCHIVIO, copiala
        expected_path = os.path.join(dest_folder, os.path.basename(photo_path))
        if not os.path.exists(expected_path):
            copy_file_with_duplicate_handling(photo_path, dest_folder)

    def get_existing_highlights(self):
        """Ottiene lista delle cartelle highlights esistenti (ordinate per data creazione, più recenti prima)"""
        if not os.path.exists(self.highlights_folder):
            return []

        highlights = []
        for item in os.listdir(self.highlights_folder):
            item_path = os.path.join(self.highlights_folder, item)
            if os.path.isdir(item_path):
                # Ottieni data di creazione
                creation_time = os.path.getctime(item_path)
                highlights.append((item, creation_time))

        # Ordina per data creazione DECRESCENTE (più recenti prima)
        highlights.sort(key=lambda x: x[1], reverse=True)

        # Ritorna solo i nomi
        return [name for name, _ in highlights]

    def count_photos_in_highlight(self, highlight_name):
        """Conta il numero di foto in un highlight"""
        highlight_path = os.path.join(self.highlights_folder, highlight_name)

        if not os.path.exists(highlight_path) or not os.path.isdir(highlight_path):
            return 0

        # Conta solo i file (non le sottocartelle)
        count = 0
        for item in os.listdir(highlight_path):
            item_path = os.path.join(highlight_path, item)
            if os.path.isfile(item_path):
                # Opzionale: filtra solo immagini comuni
                if item.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif')):
                    count += 1

        return count