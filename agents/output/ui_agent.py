"""
UIAgent — versione essenziale
GUI tkinter per visualizzare e organizzare le foto.
"""
import logging
import os
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog

from ui.components import (
    PhotoProgressBar, ToastNotification,
    ActionButton, InfoBar, StatusBar, THEME, FONTS
)

logger = logging.getLogger(__name__)


class UIAgent:
    """Agente UI con GUI tkinter."""

    def __init__(
        self,
        photo_manager=None,
        folder_manager_agent=None,
        path_guard=None,
        audit_logger=None,
        orchestrator=None,
    ):
        self.photo_manager = photo_manager
        self.folder_manager_agent = folder_manager_agent
        self.path_guard = path_guard
        self.audit_logger = audit_logger
        self.orchestrator = orchestrator

        import config as _cfg
        self._default_source = getattr(_cfg, 'SOURCE_FOLDER', '')
        self._default_dest = getattr(_cfg, 'DESTINATION_FOLDER', '')
        self.source_folder = None   # creato in run() dopo tk.Tk()
        self.dest_folder = None

        self.root = None
        self._toast = ToastNotification()
        self._stats = {'moved': 0, 'errors': 0}
        self._progress_bar = None
        self._info_bar = None
        self._status_bar = None

    def run(self):
        """Avvia la GUI principale."""
        self.root = tk.Tk()
        self.source_folder = tk.StringVar(master=self.root, value=self._default_source)
        self.dest_folder = tk.StringVar(master=self.root, value=self._default_dest)
        self.root.title("📸 Photo Organizer v2")
        self.root.configure(bg=THEME['bg_primary'])
        self.root.minsize(
            getattr(__import__('config'), 'MIN_WIDTH', 1000),
            getattr(__import__('config'), 'MIN_HEIGHT', 700)
        )
        self.root.geometry(
            f"{getattr(__import__('config'), 'DEFAULT_WIDTH', 1400)}"
            f"x{getattr(__import__('config'), 'DEFAULT_HEIGHT', 900)}"
        )

        self._build_folder_selector()
        self._build_header()
        self._build_main_area()
        self._build_action_bar()
        self._build_status_bar()

        self.root.mainloop()

    # ── Build UI ──────────────────────────────────────────────────

    def _build_folder_selector(self):
        """Pannello per selezionare le cartelle sorgente e destinazione."""
        panel = tk.Frame(self.root, bg=THEME['bg_secondary'], pady=8)
        panel.pack(fill='x')

        label_w = 12

        # Riga sorgente
        row1 = tk.Frame(panel, bg=THEME['bg_secondary'])
        row1.pack(fill='x', padx=15, pady=2)
        tk.Label(row1, text="Sorgente:", width=label_w, anchor='w',
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_secondary'], fg=THEME['text_secondary']).pack(side='left')
        tk.Entry(row1, textvariable=self.source_folder,
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_tertiary'], fg=THEME['text_primary'],
                 insertbackground=THEME['text_primary'], relief='flat',
                 width=60).pack(side='left', padx=(0, 6))
        tk.Button(row1, text="Sfoglia…",
                  font=(FONTS['family'], FONTS['size_sm']),
                  bg=THEME['accent_blue'], fg='white', relief='flat',
                  cursor='hand2',
                  command=lambda: self._browse_folder(self.source_folder)
                  ).pack(side='left')

        # Riga destinazione
        row2 = tk.Frame(panel, bg=THEME['bg_secondary'])
        row2.pack(fill='x', padx=15, pady=2)
        tk.Label(row2, text="Destinazione:", width=label_w, anchor='w',
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_secondary'], fg=THEME['text_secondary']).pack(side='left')
        tk.Entry(row2, textvariable=self.dest_folder,
                 font=(FONTS['family'], FONTS['size_sm']),
                 bg=THEME['bg_tertiary'], fg=THEME['text_primary'],
                 insertbackground=THEME['text_primary'], relief='flat',
                 width=60).pack(side='left', padx=(0, 6))
        tk.Button(row2, text="Sfoglia…",
                  font=(FONTS['family'], FONTS['size_sm']),
                  bg=THEME['accent_blue'], fg='white', relief='flat',
                  cursor='hand2',
                  command=lambda: self._browse_folder(self.dest_folder)
                  ).pack(side='left')

        # Pulsante Avvia
        tk.Button(panel, text="▶  Avvia",
                  font=(FONTS['family'], FONTS['size_sm'], FONTS['weight_bold']),
                  bg=THEME['accent_green'], fg='white', relief='flat',
                  cursor='hand2', padx=14, pady=4,
                  command=self._run_pipeline
                  ).pack(pady=(6, 0))

    def _browse_folder(self, var: tk.StringVar):
        """Apre il dialogo di selezione cartella e aggiorna la variabile."""
        initial = var.get() if var.get() and os.path.isdir(var.get()) else '/'
        chosen = filedialog.askdirectory(parent=self.root, initialdir=initial)
        if chosen:
            var.set(chosen)

    def _run_pipeline(self):
        """Esegue la pipeline con le cartelle selezionate."""
        src = self.source_folder.get().strip()
        dst = self.dest_folder.get().strip()

        if not src or not os.path.isdir(src):
            messagebox.showerror("Cartella non valida",
                                 "Seleziona una cartella sorgente valida.",
                                 parent=self.root)
            return
        if not dst:
            messagebox.showerror("Cartella non valida",
                                 "Seleziona una cartella di destinazione.",
                                 parent=self.root)
            return

        if not self.orchestrator:
            self._toast.show(self.root, "Orchestratore non disponibile", 'error')
            return

        if self.path_guard:
            self.path_guard.add_allowed_root(src)
            self.path_guard.add_allowed_root(dst)

        try:
            stats = self.orchestrator.run(src, dst)
            self._stats['moved'] = stats.get('moved', 0)
            self._stats['errors'] = stats.get('errors', 0)
            self._update_status()
            self._update_highlights_list()
            self._toast.show(
                self.root,
                f"Pipeline completata: {stats.get('moved', 0)} foto organizzate",
                'success'
            )
        except Exception as e:
            logger.error("Errore pipeline: %s", e)
            self._toast.show(self.root, f"Errore: {e}", 'error')

    def _build_header(self):
        header = tk.Frame(self.root, bg=THEME['bg_secondary'], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="📸 Photo Organizer v2",
                 font=(FONTS['family'], FONTS['size_lg'], FONTS['weight_bold']),
                 bg=THEME['bg_secondary'], fg=THEME['accent_gold']).pack(side='left', padx=20, pady=10)

        progress_frame = tk.Frame(header, bg=THEME['bg_secondary'])
        progress_frame.pack(side='left', fill='x', expand=True, padx=20)

        self._progress_label = tk.Label(
            progress_frame, text="Foto 0/0  0%",
            font=(FONTS['family'], FONTS['size_sm']),
            bg=THEME['bg_secondary'], fg=THEME['text_secondary']
        )
        self._progress_label.pack(anchor='w')
        self._progress_bar = PhotoProgressBar(progress_frame, total=1)
        self._progress_bar.pack(fill='x', pady=2)

        btn_frame = tk.Frame(header, bg=THEME['bg_secondary'])
        btn_frame.pack(side='right', padx=15)

        tk.Button(
            btn_frame, text="⚙️", font=(FONTS['family'], 14),
            bg=THEME['bg_secondary'], fg=THEME['text_secondary'],
            relief='flat', cursor='hand2'
        ).pack(side='left', padx=4)

    def _build_main_area(self):
        main = tk.Frame(self.root, bg=THEME['bg_primary'])
        main.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(
            main, bg=THEME['bg_tertiary'],
            highlightthickness=0
        )
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        right = tk.Frame(main, bg=THEME['bg_secondary'], width=320)
        right.pack(side='right', fill='y')
        right.pack_propagate(False)

        tk.Label(right, text="⭐ HIGHLIGHTS",
                 font=(FONTS['family'], FONTS['size_md'], FONTS['weight_bold']),
                 bg=THEME['bg_secondary'], fg=THEME['accent_gold']).pack(pady=(15, 5))

        self._highlights_list = tk.Listbox(
            right, bg=THEME['bg_tertiary'], fg=THEME['text_primary'],
            font=(FONTS['family'], FONTS['size_sm']),
            selectbackground=THEME['accent_blue'],
            relief='flat', borderwidth=0, height=15
        )
        self._highlights_list.pack(fill='x', padx=10)

        self._info_bar = InfoBar(self.root)
        self._info_bar.pack(fill='x')

    def _build_action_bar(self):
        action_bar = tk.Frame(self.root, bg=THEME['bg_secondary'], height=80)
        action_bar.pack(fill='x')
        action_bar.pack_propagate(False)

        buttons_frame = tk.Frame(action_bar, bg=THEME['bg_secondary'])
        buttons_frame.pack(expand=True)

        ActionButton(
            buttons_frame, icon='🗑️', label='Elimina', shortcut='Del',
            command=self._delete_photo, color=THEME['accent_red']
        ).pack(side='left', padx=4, pady=10)

        ActionButton(
            buttons_frame, icon='⏭️', label='Salta', shortcut='→',
            command=self._skip_photo, color=THEME['text_muted']
        ).pack(side='left', padx=4, pady=10)

        ActionButton(
            buttons_frame, icon='⭐', label='Highlight', shortcut='H',
            command=self._new_highlight, color=THEME['accent_gold']
        ).pack(side='left', padx=4, pady=10)

        ActionButton(
            buttons_frame, icon='⬅️', label='Indietro', shortcut='←',
            command=self._go_back, color=THEME['accent_blue']
        ).pack(side='left', padx=4, pady=10)

    def _build_status_bar(self):
        self._status_bar = StatusBar(self.root)
        self._status_bar.pack(fill='x', side='bottom')

    # ── Azioni ───────────────────────────────────────────────────

    def _delete_photo(self):
        """Elimina la foto corrente via send2trash con conferma."""
        if not messagebox.askyesno(
            "Conferma eliminazione",
            "Eliminare questa foto nel cestino di sistema?\n(Reversibile)"
        ):
            return

        photo_path = self._get_current_photo()
        if not photo_path:
            return

        try:
            from send2trash import send2trash
            if self.audit_logger:
                self.audit_logger.log_delete(photo_path)
            send2trash(photo_path)
            self._stats['moved'] = max(0, self._stats['moved'] - 1)
            self._update_status()
            self._toast.show(self.root, "Foto spostata nel cestino", 'success')
        except Exception as e:
            logger.error("Errore eliminazione: %s", e)
            self._toast.show(self.root, f"Errore: {e}", 'error')

    def _skip_photo(self):
        """Salta la foto corrente."""
        logger.debug("Skip foto")

    def _go_back(self):
        """Torna alla foto precedente."""
        logger.debug("Vai indietro")

    def _new_highlight(self):
        """Crea un nuovo highlight dalla foto corrente."""
        photo_path = self._get_current_photo()
        if not photo_path or not self.folder_manager_agent:
            return

        name = simpledialog.askstring(
            "Nuovo Highlight", "Nome del nuovo highlight:",
            parent=self.root
        )
        if not name:
            return

        try:
            if self.path_guard:
                clean_name = self.path_guard.validate_highlight_name(name)
            else:
                clean_name = name.strip()

            from core.orchestrator import PhotoMetadata
            from datetime import datetime
            meta = PhotoMetadata(
                original_path=photo_path,
                current_path=photo_path,
                date=datetime.now()
            )
            self.folder_manager_agent.move_to_highlight(meta, clean_name)
            self._toast.show(self.root, f"Aggiunto a '{clean_name}'", 'success')
            self._update_highlights_list()
        except ValueError as e:
            messagebox.showerror("Nome non valido", str(e), parent=self.root)
        except Exception as e:
            logger.error("Errore highlight: %s", e)
            self._toast.show(self.root, f"Errore: {e}", 'error')

    # ── Utilities ────────────────────────────────────────────────

    def _get_current_photo(self) -> str:
        """Ritorna il path della foto corrente."""
        if self.photo_manager and hasattr(self.photo_manager, 'get_current_photo'):
            return self.photo_manager.get_current_photo()
        return ''

    def _load_photo(self, photo_path: str):
        """Carica una foto nel canvas."""
        if not photo_path or not self.canvas:
            return

        try:
            from PIL import Image, ImageTk
            with Image.open(photo_path) as img:
                w = self.canvas.winfo_width() or 800
                h = self.canvas.winfo_height() or 600
                img.thumbnail((w, h))
                thumbnail = img.copy()
            self._photo_ref = ImageTk.PhotoImage(thumbnail)
            self.canvas.delete('all')
            cx = self.canvas.winfo_width() // 2
            cy = self.canvas.winfo_height() // 2
            self.canvas.create_image(cx, cy, image=self._photo_ref, anchor='center')
        except Exception as e:
            logger.debug("Errore visualizzazione foto: %s", e)
            self.canvas.delete('all')
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text="⚠️ Immagine non valida",
                fill=THEME['accent_red'],
                font=(FONTS['family'], FONTS['size_lg'])
            )

    def _on_canvas_resize(self, event=None):
        """Ricarica la foto quando il canvas cambia dimensione."""
        photo_path = self._get_current_photo()
        if photo_path:
            self._load_photo(photo_path)

    def _update_status(self):
        """Aggiorna la status bar."""
        if self._status_bar:
            self._status_bar.update_counts(
                moved=self._stats.get('moved', 0),
                errors=self._stats.get('errors', 0),
            )

    def _update_highlights_list(self):
        """Aggiorna la lista highlight nel pannello destro."""
        if not self._highlights_list or not self.folder_manager_agent:
            return
        try:
            dest = self.dest_folder.get().strip()
            if dest:
                highlights = self.folder_manager_agent.get_existing_highlights(dest)
                self._highlights_list.delete(0, tk.END)
                for h in highlights:
                    self._highlights_list.insert(tk.END, f"⭐ {h}")
        except Exception as e:
            logger.debug("Update highlights list error: %s", e)
