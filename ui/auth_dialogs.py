"""
Auth Dialogs — Fase 6, step 33
PinSetupDialog, LoginDialog, LockScreenDialog.
PIN raccolto come bytearray (azzerabile).
Shake animation su errore.
"""
import logging
import tkinter as tk
from tkinter import font as tkfont

import config

logger = logging.getLogger(__name__)

THEME = getattr(config, 'THEME', {
    'bg_primary':    '#0f1117',
    'bg_secondary':  '#1a1d27',
    'bg_tertiary':   '#252836',
    'accent_gold':   '#f5a623',
    'accent_red':    '#e74c3c',
    'text_primary':  '#ffffff',
    'text_secondary':'#a0aec0',
    'border':        '#2d3748',
    'border_focus':  '#4a9eff',
})

FONTS = getattr(config, 'FONTS', {
    'family': 'Segoe UI',
    'family_mono': 'Consolas',
    'size_xl': 18,
    'size_lg': 14,
    'size_md': 12,
    'size_sm': 10,
    'weight_bold': 'bold',
    'weight_normal': 'normal',
})


class PinSetupDialog(tk.Toplevel):
    """
    Dialog per la configurazione del PIN al primo avvio.
    PIN gestito come bytearray (azzerabile dopo l'uso).
    """

    def __init__(self, parent, auth_agent):
        super().__init__(parent)
        self.auth = auth_agent
        self.result = False

        self.title("Configura PIN — Photo Organizer")
        self.geometry("400x420")
        self.resizable(False, False)
        self.configure(bg=THEME['bg_primary'])

        # Centra sulla finestra parent
        self.transient(parent)
        self.grab_set()
        self._center(parent)

        self._build_ui()

    def _build_ui(self):
        # Icona + titolo
        tk.Label(self, text="📸", font=(FONTS['family'], 32),
                 bg=THEME['bg_primary'], fg=THEME['text_primary']).pack(pady=(30, 5))
        tk.Label(self, text="Photo Organizer",
                 font=(FONTS['family'], FONTS['size_xl'], FONTS['weight_bold']),
                 bg=THEME['bg_primary'], fg=THEME['text_primary']).pack()
        tk.Label(self, text="Imposta il tuo PIN di accesso",
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_primary'], fg=THEME['text_secondary']).pack(pady=(5, 20))

        # Card
        card = tk.Frame(self, bg=THEME['bg_secondary'],
                        highlightbackground=THEME['border'], highlightthickness=1)
        card.pack(padx=30, pady=5, fill='x')

        # Campo PIN
        tk.Label(card, text="PIN (min. 4 caratteri):",
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_secondary'], fg=THEME['text_secondary']).pack(
            anchor='w', padx=15, pady=(15, 3))
        self.pin_var = tk.StringVar()
        self.pin_entry = tk.Entry(
            card, textvariable=self.pin_var, show='●',
            font=(FONTS['family_mono'], FONTS['size_lg']),
            bg=THEME['bg_tertiary'], fg=THEME['text_primary'],
            insertbackground=THEME['text_primary'],
            relief='flat', bd=5
        )
        self.pin_entry.pack(padx=15, pady=(0, 10), fill='x')

        # Campo conferma
        tk.Label(card, text="Conferma PIN:",
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_secondary'], fg=THEME['text_secondary']).pack(
            anchor='w', padx=15, pady=(5, 3))
        self.confirm_var = tk.StringVar()
        self.confirm_entry = tk.Entry(
            card, textvariable=self.confirm_var, show='●',
            font=(FONTS['family_mono'], FONTS['size_lg']),
            bg=THEME['bg_tertiary'], fg=THEME['text_primary'],
            insertbackground=THEME['text_primary'],
            relief='flat', bd=5
        )
        self.confirm_entry.pack(padx=15, pady=(0, 15), fill='x')

        # Bottone
        btn = tk.Button(
            self, text="Configura PIN",
            font=(FONTS['family'], FONTS['size_lg'], FONTS['weight_bold']),
            bg=THEME['accent_gold'], fg='#000',
            relief='flat', cursor='hand2',
            command=self._on_submit
        )
        btn.pack(padx=30, pady=15, fill='x')
        btn.bind('<Enter>', lambda e: btn.config(bg='#d4891e'))
        btn.bind('<Leave>', lambda e: btn.config(bg=THEME['accent_gold']))

        # Messaggio errore
        self.error_label = tk.Label(
            self, text='',
            font=(FONTS['family'], FONTS['size_sm']),
            bg=THEME['bg_primary'], fg=THEME['accent_red']
        )
        self.error_label.pack()

        self.pin_entry.focus()
        self.bind('<Return>', lambda e: self._on_submit())

    def _on_submit(self):
        pin_str = self.pin_var.get()
        confirm_str = self.confirm_var.get()

        # Pulisci UI subito
        self.pin_var.set('')
        self.confirm_var.set('')

        if pin_str != confirm_str:
            self.error_label.config(text="I PIN non coincidono")
            self._shake(self.pin_entry)
            return

        # Converti in bytearray (azzerabile)
        pin_bytes = bytearray(pin_str.encode('utf-8'))
        # Azzera stringa locale
        pin_str = ' ' * len(pin_str)
        confirm_str = ' ' * len(confirm_str)

        ok, msg = self.auth.setup_pin(pin_bytes)
        # pin_bytes già azzerato da setup_pin()

        if ok:
            self.result = True
            self.destroy()
        else:
            self.error_label.config(text=msg)
            self._shake(self.pin_entry)

    def _shake(self, widget):
        """Animazione shake sul widget."""
        x0 = widget.winfo_x()
        for delta in [8, -8, 6, -6, 4, -4, 0]:
            self.after(30 * abs(delta), lambda d=delta: widget.place_configure(x=x0 + d)
                       if widget.winfo_manager() == 'place' else None)

    def _center(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")


class LoginDialog(tk.Toplevel):
    """
    Dialog di login con PIN.
    PIN gestito come bytearray. Shake animation su errore.
    """

    def __init__(self, parent, auth_agent, anomaly_detector=None):
        super().__init__(parent)
        self.auth = auth_agent
        self.anomaly_detector = anomaly_detector
        self.result = False
        self._attempts = 0

        self.title("Accedi — Photo Organizer")
        self.geometry("400x350")
        self.resizable(False, False)
        self.configure(bg=THEME['bg_primary'])

        self.transient(parent)
        self.grab_set()
        self._center(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="📸", font=(FONTS['family'], 32),
                 bg=THEME['bg_primary'], fg=THEME['text_primary']).pack(pady=(25, 5))
        tk.Label(self, text="Photo Organizer",
                 font=(FONTS['family'], FONTS['size_xl'], FONTS['weight_bold']),
                 bg=THEME['bg_primary'], fg=THEME['text_primary']).pack()
        tk.Label(self, text="Inserisci il PIN per accedere",
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_primary'], fg=THEME['text_secondary']).pack(pady=(3, 15))

        card = tk.Frame(self, bg=THEME['bg_secondary'],
                        highlightbackground=THEME['border'], highlightthickness=1)
        card.pack(padx=30, pady=5, fill='x')

        tk.Label(card, text="PIN:",
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_secondary'], fg=THEME['text_secondary']).pack(
            anchor='w', padx=15, pady=(15, 3))
        self.pin_var = tk.StringVar()
        self.pin_entry = tk.Entry(
            card, textvariable=self.pin_var, show='●',
            font=(FONTS['family_mono'], FONTS['size_lg']),
            bg=THEME['bg_tertiary'], fg=THEME['text_primary'],
            insertbackground=THEME['text_primary'],
            relief='flat', bd=5
        )
        self.pin_entry.pack(padx=15, pady=(0, 15), fill='x')

        btn = tk.Button(
            self, text="Accedi",
            font=(FONTS['family'], FONTS['size_lg'], FONTS['weight_bold']),
            bg=THEME['accent_gold'], fg='#000',
            relief='flat', cursor='hand2',
            command=self._on_submit
        )
        btn.pack(padx=30, pady=10, fill='x')
        btn.bind('<Enter>', lambda e: btn.config(bg='#d4891e'))
        btn.bind('<Leave>', lambda e: btn.config(bg=THEME['accent_gold']))

        self.error_label = tk.Label(
            self, text='',
            font=(FONTS['family'], FONTS['size_sm']),
            bg=THEME['bg_primary'], fg=THEME['accent_red']
        )
        self.error_label.pack(pady=5)

        self.pin_entry.focus()
        self.bind('<Return>', lambda e: self._on_submit())

    def _on_submit(self):
        pin_str = self.pin_var.get()
        self.pin_var.set('')
        self.pin_entry.delete(0, tk.END)

        pin_bytes = bytearray(pin_str.encode('utf-8'))
        pin_str = ' ' * len(pin_str)  # Azzera stringa locale

        ok, msg = self.auth.authenticate(pin_bytes)
        # pin_bytes già azzerato da authenticate()

        if ok:
            self.result = True
            self.destroy()
        else:
            self._attempts += 1
            if self.anomaly_detector:
                self.anomaly_detector.on_auth_failure(self._attempts)
            self.error_label.config(text=msg)
            self._shake_entry()

    def _on_cancel(self):
        self.result = False
        self.destroy()

    def _shake_entry(self):
        """Animazione shake sul campo PIN."""
        entry = self.pin_entry
        orig_bg = THEME['bg_tertiary']
        # Flash rosso + shake
        entry.config(bg='#4a1515')
        self.after(150, lambda: entry.config(bg=orig_bg))

        # Shake orizzontale usando pack con padx alternato
        steps = [10, -10, 8, -8, 5, -5, 0]
        for i, delta in enumerate(steps):
            self.after(i * 40, lambda d=delta: entry.pack_configure(
                padx=(15 + d, 15 - d)
            ))

    def _center(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = 400, 350
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")


class LockScreenDialog(tk.Toplevel):
    """
    Schermata di blocco dopo timeout sessione.
    Richiede re-autenticazione con PIN.
    """

    def __init__(self, parent, auth_agent, anomaly_detector=None):
        super().__init__(parent)
        self.auth = auth_agent
        self.anomaly_detector = anomaly_detector
        self.result = False

        self.title("Sessione scaduta")
        self.geometry("400x300")
        self.resizable(False, False)
        self.configure(bg=THEME['bg_primary'])

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._center(parent)

        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="🔒",
                 font=(FONTS['family'], 36),
                 bg=THEME['bg_primary'], fg=THEME['accent_gold']).pack(pady=(25, 5))
        tk.Label(self, text="Sessione scaduta",
                 font=(FONTS['family'], FONTS['size_xl'], FONTS['weight_bold']),
                 bg=THEME['bg_primary'], fg=THEME['text_primary']).pack()
        tk.Label(self, text="Inserisci il PIN per sbloccare",
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_primary'], fg=THEME['text_secondary']).pack(pady=(3, 15))

        card = tk.Frame(self, bg=THEME['bg_secondary'],
                        highlightbackground=THEME['border'], highlightthickness=1)
        card.pack(padx=30, fill='x')

        self.pin_var = tk.StringVar()
        self.pin_entry = tk.Entry(
            card, textvariable=self.pin_var, show='●',
            font=(FONTS['family_mono'], FONTS['size_lg']),
            bg=THEME['bg_tertiary'], fg=THEME['text_primary'],
            insertbackground=THEME['text_primary'],
            relief='flat', bd=5
        )
        self.pin_entry.pack(padx=15, pady=15, fill='x')

        btn = tk.Button(
            self, text="Sblocca",
            font=(FONTS['family'], FONTS['size_lg'], FONTS['weight_bold']),
            bg=THEME['accent_gold'], fg='#000',
            relief='flat', cursor='hand2',
            command=self._on_submit
        )
        btn.pack(padx=30, pady=10, fill='x')

        self.error_label = tk.Label(
            self, text='',
            font=(FONTS['family'], FONTS['size_sm']),
            bg=THEME['bg_primary'], fg=THEME['accent_red']
        )
        self.error_label.pack()

        self.pin_entry.focus()
        self.bind('<Return>', lambda e: self._on_submit())

    def _on_submit(self):
        pin_str = self.pin_var.get()
        self.pin_var.set('')

        pin_bytes = bytearray(pin_str.encode('utf-8'))
        pin_str = ' ' * len(pin_str)

        ok, msg = self.auth.authenticate(pin_bytes)

        if ok:
            self.result = True
            self.destroy()
        else:
            if self.anomaly_detector:
                self.anomaly_detector.on_auth_failure(1)
            self.error_label.config(text=msg)
            self.pin_entry.config(bg='#4a1515')
            self.after(200, lambda: self.pin_entry.config(bg=THEME['bg_tertiary']))

    def _on_cancel(self):
        self.result = False
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        self.geometry(f"+{px + (pw - 400) // 2}+{py + (ph - 300) // 2}")
