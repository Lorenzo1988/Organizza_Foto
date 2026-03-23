import tkinter as tk
from config import COLORS


def create_styled_button(parent, text, command, bg_color, active_bg_color):
    """Crea un bottone stilizzato"""
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg_color,
        fg='white',
        activebackground=active_bg_color,
        font=('Arial', 12, 'bold'),
        height=2,
        cursor='hand2'
    )
    return btn


def create_header(parent, initial_text=""):
    """Crea l'header con progress bar"""
    header_frame = tk.Frame(parent, bg=COLORS['header_bg'], height=60)
    header_frame.pack(fill='x', side='top')
    header_frame.pack_propagate(False)

    progress_label = tk.Label(
        header_frame,
        text=initial_text,
        font=('Arial', 14, 'bold'),
        bg=COLORS['header_bg'],
        fg=COLORS['header_fg']
    )
    progress_label.pack(pady=15)

    return progress_label


def create_info_panel(parent):
    """Crea il pannello informazioni"""
    info_frame = tk.Frame(parent, bg=COLORS['main_bg'], height=80)
    info_frame.pack(fill='x', side='top')
    info_frame.pack_propagate(False)

    info_label = tk.Label(
        info_frame,
        text="",
        font=('Arial', 11),
        bg=COLORS['main_bg'],
        fg=COLORS['info_fg'],
        justify='left'
    )
    info_label.pack(pady=10, padx=20)

    return info_label


def create_canvas(parent):
    """Crea il canvas per visualizzare le immagini"""
    canvas = tk.Canvas(parent, bg=COLORS['canvas_bg'], highlightthickness=0)
    canvas.pack(fill='both', expand=True)
    return canvas