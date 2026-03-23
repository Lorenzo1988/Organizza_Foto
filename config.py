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

# ── Yearly Best Collector ──────────────────────────────────────────────────
YEARLY_BEST_FOLDER_NAME = "📅 MIGLIORI_ANNO"
YEARLY_BEST_COUNT = 12          # numero di foto per anno, modifica a piacere

# ── Sicurezza ──────────────────────────────────────────────────────────────
AUDIT_LOG_FILE = "audit_log.txt"
MAX_PHOTO_SIZE_MB = 200         # file più grandi vengono ignorati

# ── Duplicati ──────────────────────────────────────────────────────────────
DUPLICATE_HASH_THRESHOLD = 8    # distanza Hamming per perceptual hash (0=identici)

# ── Design System ─────────────────────────────────────────────────────────
import platform as _platform

def _get_system_font():
    s = _platform.system()
    if s == 'Windows':
        return 'Segoe UI'
    elif s == 'Darwin':
        return 'SF Pro Display'
    return 'Ubuntu'

THEME = {
    'bg_primary':    '#0f1117',
    'bg_secondary':  '#1a1d27',
    'bg_tertiary':   '#252836',
    'bg_hover':      '#2e3148',
    'accent_gold':   '#f5a623',
    'accent_blue':   '#4a9eff',
    'accent_green':  '#2ecc71',
    'accent_red':    '#e74c3c',
    'accent_purple': '#9b59b6',
    'text_primary':  '#ffffff',
    'text_secondary':'#a0aec0',
    'text_muted':    '#4a5568',
    'border':        '#2d3748',
    'border_focus':  '#4a9eff',
    'overlay':       '#00000088',
    'shadow':        '#00000044',
}

THEME_LIGHT = {
    'bg_primary':    '#f7f8fc',
    'bg_secondary':  '#ffffff',
    'bg_tertiary':   '#edf2f7',
    'bg_hover':      '#e2e8f0',
    'accent_gold':   '#d97706',
    'accent_blue':   '#2563eb',
    'accent_green':  '#16a34a',
    'accent_red':    '#dc2626',
    'accent_purple': '#7c3aed',
    'text_primary':  '#1a202c',
    'text_secondary':'#4a5568',
    'text_muted':    '#a0aec0',
    'border':        '#e2e8f0',
    'border_focus':  '#2563eb',
    'overlay':       '#00000066',
    'shadow':        '#0000001a',
}

FONTS = {
    'family':        _get_system_font(),
    'family_mono':   'Consolas',
    'size_xl':    18,
    'size_lg':    14,
    'size_md':    12,
    'size_sm':    10,
    'size_xs':     9,
    'weight_bold':   'bold',
    'weight_normal': 'normal',
}

# ── Dimensioni finestra ────────────────────────────────────────────────────
MIN_WIDTH  = 1000
MIN_HEIGHT = 700
DEFAULT_WIDTH  = 1400
DEFAULT_HEIGHT = 900