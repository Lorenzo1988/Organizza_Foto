import os

# Percorsi
SOURCE_FOLDER = r"C:\Users\loren\OneDrive\Desktop\Archivio_Foto\20251012_Scarico_Android"
DESTINATION_FOLDER = r"C:\Users\loren\OneDrive\Desktop\Archivio_Foto\20251012_Scarico_Android_Organizzato"

# File eventi e progressi
EVENTS_FILE = "file_eventi.txt"
PROGRESS_FILE = "progress_checkpoint.txt"

# Nomi cartelle principali
HIGHLIGHTS_FOLDER_NAME = "⭐ HIGHLIGHTS"
EVENTS_FOLDER_NAME = "📅 EVENTI"
ARCHIVE_FOLDER_NAME = "📸 ARCHIVIO"
TO_PRINT_FOLDER_NAME = "🖨️ DA_STAMPARE"

# Estensioni foto supportate
PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic'}

# Nomi mesi
MONTH_NAMES = {
    1: "01_Gennaio", 2: "02_Febbraio", 3: "03_Marzo",
    4: "04_Aprile", 5: "05_Maggio", 6: "06_Giugno",
    7: "07_Luglio", 8: "08_Agosto", 9: "09_Settembre",
    10: "10_Ottobre", 11: "11_Novembre", 12: "12_Dicembre"
}

# Soglia giorni per compleanni
BIRTHDAY_THRESHOLD_DAYS = 7

# Colori UI
COLORS = {
    'header_bg': '#2c3e50',
    'header_fg': 'white',
    'main_bg': '#ecf0f1',
    'canvas_bg': '#34495e',
    'info_fg': '#2c3e50',
    'delete_btn': '#e74c3c',
    'delete_btn_active': '#c0392b',
    'skip_btn': '#95a5a6',
    'skip_btn_active': '#7f8c8d',
    'highlight_btn': '#f39c12',
    'highlight_btn_active': '#e67e22',
    'back_btn': '#3498db',
    'back_btn_active': '#2980b9',
    'existing_highlight_btn': '#27ae60',
    'print_btn': '#9b59b6',
    'print_btn_active': '#8e44ad'
}