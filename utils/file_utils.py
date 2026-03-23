import os
import shutil
import re
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from config import PHOTO_EXTENSIONS


def load_all_photos(source_folder):
    """Carica tutte le foto dalla cartella sorgente"""
    photos = []

    for root, dirs, files in os.walk(source_folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_ext = Path(filename).suffix.lower()
            if file_ext in PHOTO_EXTENSIONS:
                photos.append(file_path)

    return sorted(photos)


def extract_date_from_filename(filename):
    """
    Estrae la data dal nome del file se presente nel formato yyyymmdd
    Cerca pattern come: 20240315, IMG_20240315, 2024-03-15, etc.
    """
    # Pattern per cercare yyyymmdd nel nome del file
    patterns = [
        r'(\d{4})(\d{2})(\d{2})',  # 20240315
        r'(\d{4})[_-](\d{2})[_-](\d{2})',  # 2024-03-15 o 2024_03_15
        r'(\d{4})\.(\d{2})\.(\d{2})',  # 2024.03.15
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))

                # Verifica che la data sia valida
                if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                    return datetime(year, month, day)
            except (ValueError, IndexError):
                continue

    return None


def get_photo_date(file_path):
    """
    Estrae la data di scatto dalla foto con priorità:
    1. Data dal nome del file (se presente nel formato yyyymmdd)
    2. Metadati EXIF
    3. Data di modifica del file
    """
    filename = os.path.basename(file_path)

    # PRIORITÀ 1: Cerca data nel nome del file
    date_from_filename = extract_date_from_filename(filename)
    if date_from_filename:
        return date_from_filename

    # PRIORITÀ 2: Cerca nei metadati EXIF
    try:
        image = Image.open(file_path)
        exif_data = image._getexif()

        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "DateTimeOriginal":
                    date_str = value.split()[0]
                    return datetime.strptime(date_str, "%Y:%m:%d")
    except:
        pass

    # PRIORITÀ 3: Fallback - usa la data di modifica del file
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp)


def copy_file_with_duplicate_handling(source_path, dest_folder):
    """Copia un file gestendo i duplicati"""
    os.makedirs(dest_folder, exist_ok=True)

    filename = os.path.basename(source_path)
    dest_path = os.path.join(dest_folder, filename)

    # Gestisci duplicati
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            new_filename = f"{base}_{counter}{ext}"
            dest_path = os.path.join(dest_folder, new_filename)
            counter += 1

    shutil.copy2(source_path, dest_path)
    return dest_path