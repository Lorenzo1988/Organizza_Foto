"""
UI Components — Fase 6, step 34
PhotoProgressBar, ToastNotification, ActionButton, InfoBar, StatusBar.
Tutti i colori/font da THEME e FONTS in config.py.

Mantiene retrocompatibilità: create_styled_button ancora disponibile.
"""
import logging
import tkinter as tk
from typing import Callable, Optional

import config

logger = logging.getLogger(__name__)

THEME = getattr(config, 'THEME', {
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
})

FONTS = getattr(config, 'FONTS', {
    'family':        'Segoe UI',
    'family_mono':   'Consolas',
    'size_xl':    18,
    'size_lg':    14,
    'size_md':    12,
    'size_sm':    10,
    'size_xs':     9,
    'weight_bold':   'bold',
    'weight_normal': 'normal',
})

# Retrocompatibilità con codice esistente
COLORS = getattr(config, 'COLORS', {})


def create_styled_button(parent, text, command, bg_color, active_bg_color,
                         font=None, **kwargs):
    """Retrocompatibilità con la versione originale di components.py."""
    if font is None:
        font = (FONTS['family'], FONTS['size_md'], FONTS['weight_bold'])
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg_color, activebackground=active_bg_color,
        fg=THEME.get('text_primary', 'white'),
        font=font, relief='flat', cursor='hand2',
        **kwargs
    )
    return btn


class PhotoProgressBar(tk.Canvas):
    """
    Barra progresso custom con colore variabile e aggiornamento smooth.
    """

    def __init__(self, parent, total: int = 100, **kwargs):
        kwargs.setdefault('bg', THEME['bg_primary'])
        kwargs.setdefault('highlightthickness', 0)
        super().__init__(parent, height=8, **kwargs)
        self.total = max(total, 1)
        self.current = 0
        self.bind('<Configure>', lambda e: self._draw())

    def set_total(self, total: int):
        self.total = max(total, 1)
        self._draw()

    def set_progress(self, current: int):
        self.current = current
        self._draw()

    def _draw(self):
        self.delete('all')
        w = self.winfo_width() or 200
        pct = self.current / self.total
        fill_w = int(w * pct)

        self.create_rectangle(0, 0, w, 8, fill=THEME['bg_tertiary'], outline='')

        if pct > 0.8:
            color = THEME['accent_green']
        elif pct > 0.4:
            color = THEME['accent_gold']
        else:
            color = THEME['accent_blue']

        if fill_w > 0:
            self.create_rectangle(0, 0, fill_w, 8, fill=color, outline='')


class ToastNotification:
    """
    Notifica temporanea non-invasiva (in basso a destra).
    Tipi: success, warning, error, info.
    """

    TYPES = {
        'success': ('accent_green', '✅'),
        'warning': ('accent_gold',  '⚠️'),
        'error':   ('accent_red',   '❌'),
        'info':    ('accent_blue',  'ℹ️'),
    }

    def show(self, parent, message: str, type_: str = 'info', duration_ms: int = 3000):
        """Mostra una toast notification non-bloccante."""
        color_key, icon = self.TYPES.get(type_, ('accent_blue', 'ℹ️'))
        color = THEME[color_key]

        try:
            toast = tk.Toplevel(parent)
            toast.overrideredirect(True)
            toast.attributes('-topmost', True)
            toast.configure(bg=THEME['bg_secondary'])

            # Barra colorata in cima
            tk.Frame(toast, bg=color, height=3).pack(fill='x')

            tk.Label(
                toast, text=f"{icon}  {message}",
                font=(FONTS['family'], FONTS['size_sm']),
                bg=THEME['bg_secondary'], fg=THEME['text_primary'],
                wraplength=260, justify='left', padx=12, pady=8
            ).pack()

            parent.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            tw, th = 300, 70
            x = px + pw - tw - 20
            y = py + ph - th - 40
            toast.geometry(f"{tw}x{th}+{x}+{y}")

            toast.after(duration_ms, lambda: toast.destroy() if toast.winfo_exists() else None)
        except Exception as e:
            logger.debug("ToastNotification error: %s", e)


class ActionButton(tk.Frame):
    """
    Bottone con icona, label, shortcut hint, hover effect.
    """

    def __init__(self, parent, icon: str, label: str, shortcut: str,
                 command: Callable, color: str, **kwargs):
        super().__init__(parent, bg=THEME['bg_secondary'], **kwargs)
        self._color = color
        self._command = command
        self._disabled = False

        self.configure(cursor='hand2')

        inner = tk.Frame(self, bg=color, padx=14, pady=10)
        inner.pack(fill='both', expand=True)
        self._inner = inner

        tk.Label(inner, text=icon, font=(FONTS['family'], 16),
                 bg=color, fg='white').pack()
        tk.Label(inner, text=label,
                 font=(FONTS['family'], FONTS['size_sm'], FONTS['weight_bold']),
                 bg=color, fg='white').pack()
        if shortcut:
            tk.Label(inner, text=shortcut,
                     font=(FONTS['family'], FONTS['size_xs']),
                     bg=color, fg='#cccccc').pack()

        for w in [self, inner] + list(inner.winfo_children()):
            w.bind('<Button-1>', self._on_click)
            w.bind('<Enter>', self._on_hover)
            w.bind('<Leave>', self._on_leave)

    def _on_click(self, event=None):
        if not self._disabled and self._command:
            self._command()

    def _on_hover(self, event=None):
        if not self._disabled:
            self._inner.configure(bg=THEME.get('bg_hover', '#2e3148'))

    def _on_leave(self, event=None):
        if not self._disabled:
            self._inner.configure(bg=self._color)

    def set_disabled(self, disabled: bool):
        self._disabled = disabled
        bg = THEME['text_muted'] if disabled else self._color
        self._inner.configure(bg=bg)
        self.configure(cursor='arrow' if disabled else 'hand2')


class InfoBar(tk.Frame):
    """
    Barra informazioni sulla foto corrente con badge GPS/XMP e duplicati.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=THEME['bg_secondary'], pady=5, **kwargs)

        row1 = tk.Frame(self, bg=THEME['bg_secondary'])
        row1.pack(fill='x', padx=10)
        row2 = tk.Frame(self, bg=THEME['bg_secondary'])
        row2.pack(fill='x', padx=10)

        self._lbl = {}
        for key, text, fg, row in [
            ('filename', '📄 —', THEME['text_primary'], row1),
            ('date',     '📅 —', THEME['text_secondary'], row1),
            ('folder',   '📁 —', THEME['text_secondary'], row1),
            ('camera',   '',     THEME['text_secondary'], row2),
            ('gps_badge','',     THEME['accent_green'], row2),
            ('dup_badge','',     THEME['accent_green'], row2),
        ]:
            lbl = tk.Label(row, text=text,
                           font=(FONTS['family'], FONTS['size_sm']),
                           bg=THEME['bg_secondary'], fg=fg, padx=6)
            lbl.pack(side='left')
            self._lbl[key] = lbl

    def update_info(self, filename: str = '', date: str = '', folder: str = '',
                    camera: str = '', gps_stripped: bool = False,
                    xmp_stripped: bool = False, is_duplicate: bool = False,
                    duplicate_of: str = ''):
        self._lbl['filename'].config(text=f"📄 {filename}" if filename else '📄 —')
        self._lbl['date'].config(text=f"📅 {date}" if date else '📅 —')
        self._lbl['folder'].config(text=f"📁 {folder}" if folder else '📁 —')
        self._lbl['camera'].config(text=f"🔍 {camera}" if camera else '')

        if gps_stripped or xmp_stripped:
            self._lbl['gps_badge'].config(text='📍 GPS rimosso', fg=THEME['accent_green'])
        else:
            self._lbl['gps_badge'].config(text='')

        if is_duplicate:
            short = duplicate_of[:25] + '...' if len(duplicate_of) > 25 else duplicate_of
            self._lbl['dup_badge'].config(
                text=f"🔄 Duplicato di {short}", fg=THEME['accent_red']
            )
        else:
            self._lbl['dup_badge'].config(text='✅ Originale', fg=THEME['accent_green'])


class StatusBar(tk.Frame):
    """
    Barra di stato in fondo (24px) con contatori real-time e indicatore sessione.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=THEME['bg_secondary'], height=24, **kwargs)
        self.pack_propagate(False)

        self._counters = {}
        for key, text, fg in [
            ('moved',   '✅ 0 organizzate',  THEME['accent_green']),
            ('dupes',   '🔄 0 duplicate',    THEME['accent_blue']),
            ('errors',  '',                  THEME['accent_red']),
            ('session', '🔒 —',              THEME['text_muted']),
            ('save',    '💾 Pronto',         THEME['text_muted']),
        ]:
            lbl = tk.Label(self, text=text,
                           font=(FONTS['family'], FONTS['size_xs']),
                           bg=THEME['bg_secondary'], fg=fg, padx=8)
            lbl.pack(side='left')
            self._counters[key] = lbl

    def update_counts(self, moved: int = 0, duplicates: int = 0,
                      errors: int = 0, session_minutes: int = -1,
                      saving: bool = False):
        self._counters['moved'].config(text=f"✅ {moved} organizzate")
        self._counters['dupes'].config(text=f"🔄 {duplicates} duplicate")
        self._counters['errors'].config(
            text=f"⚠️ {errors} errori" if errors > 0 else ''
        )
        if session_minutes >= 0:
            color = THEME['accent_gold'] if session_minutes < 10 else THEME['text_muted']
            self._counters['session'].config(
                text=f"🔒 Sessione: {session_minutes} min", fg=color
            )
        self._counters['save'].config(
            text='💾 Salvataggio...' if saving else '💾 Salvato',
            fg=THEME['accent_gold'] if saving else THEME['accent_green']
        )
