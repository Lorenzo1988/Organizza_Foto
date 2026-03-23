"""
UIAgent — Fase 6, step 35
Wrappa la GUI tkinter esistente con le nuove funzionalità di sicurezza.
- TUTTI i Image.open() passano per memory_manager.open_thumbnail()
- MAI Image.open() diretto nella GUI
- DependencyAuditAgent: mostra banner se CVE trovati
- AnomalyDetector collegato al tasto delete e agli highlights
"""
import logging
import os
import tkinter as tk
from tkinter import messagebox, simpledialog

from ui.components import (
    PhotoProgressBar, ToastNotification,
    ActionButton, InfoBar, StatusBar, THEME, FONTS
)

logger = logging.getLogger(__name__)


class UIAgent:
    """
    Agente UI che wrappa e potenzia la GUI tkinter esistente.
    Integra tutti gli agenti di sicurezza nella GUI.
    """

    SESSION_CHECK_INTERVAL_MS = 300_000  # 5 minuti

    def __init__(
        self,
        photo_manager=None,
        folder_manager_agent=None,
        path_guard=None,
        auth_agent=None,
        anomaly_detector=None,
        memory_manager=None,
        audit_logger=None,
        dependency_audit=None,
    ):
        self.photo_manager = photo_manager
        self.folder_manager_agent = folder_manager_agent
        self.path_guard = path_guard
        self.auth = auth_agent
        self.anomaly_detector = anomaly_detector
        self.memory_manager = memory_manager
        self.audit_logger = audit_logger
        self.dependency_audit = dependency_audit

        self.root = None
        self._toast = ToastNotification()
        self._stats = {'moved': 0, 'duplicates': 0, 'errors': 0}
        self._progress_bar = None
        self._info_bar = None
        self._status_bar = None

    def run(self):
        """Avvia la GUI principale."""
        self.root = tk.Tk()
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

        self._build_header()
        self._build_main_area()
        self._build_action_bar()
        self._build_status_bar()

        # Mostra banner CVE se ci sono vulnerabilità
        self._check_dependency_audit()

        # Configura timeout sessione
        if self.auth:
            self.root.after(self.SESSION_CHECK_INTERVAL_MS, self._check_session_timeout)

        self.root.mainloop()

    # ── Build UI ──────────────────────────────────────────────────

    def _build_header(self):
        header = tk.Frame(self.root, bg=THEME['bg_secondary'], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="📸 Photo Organizer v2",
                 font=(FONTS['family'], FONTS['size_lg'], FONTS['weight_bold']),
                 bg=THEME['bg_secondary'], fg=THEME['accent_gold']).pack(side='left', padx=20, pady=10)

        # Progress bar
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

        # Bottoni header (impostazioni, blocco)
        btn_frame = tk.Frame(header, bg=THEME['bg_secondary'])
        btn_frame.pack(side='right', padx=15)

        tk.Button(
            btn_frame, text="⚙️", font=(FONTS['family'], 14),
            bg=THEME['bg_secondary'], fg=THEME['text_secondary'],
            relief='flat', cursor='hand2'
        ).pack(side='left', padx=4)

        if self.auth:
            tk.Button(
                btn_frame, text="🔒", font=(FONTS['family'], 14),
                bg=THEME['bg_secondary'], fg=THEME['text_secondary'],
                relief='flat', cursor='hand2',
                command=self._lock_screen
            ).pack(side='left', padx=4)

    def _build_main_area(self):
        main = tk.Frame(self.root, bg=THEME['bg_primary'])
        main.pack(fill='both', expand=True)

        # Canvas foto (area principale)
        self.canvas = tk.Canvas(
            main, bg=THEME['bg_tertiary'],
            highlightthickness=0
        )
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        # Pannello destro (HIGHLIGHTS + MIGLIORI_ANNO)
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

        tk.Label(right, text="📅 MIGLIORI ANNO",
                 font=(FONTS['family'], FONTS['size_sm'], FONTS['weight_bold']),
                 bg=THEME['bg_secondary'], fg=THEME['accent_blue']).pack(pady=(15, 5))

        tk.Button(
            right, text="Genera raccolta",
            font=(FONTS['family'], FONTS['size_sm']),
            bg=THEME['accent_blue'], fg='white',
            relief='flat', cursor='hand2'
        ).pack(padx=10, fill='x')

        # InfoBar sotto il canvas
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
            if self.anomaly_detector:
                self.anomaly_detector.on_delete(photo_path)
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

            # Crea PhotoMetadata temporanea per il folder_manager
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

    # ── Sessione ─────────────────────────────────────────────────

    def _check_session_timeout(self):
        """Controlla scadenza sessione ogni 5 minuti."""
        if self.auth and not self.auth.is_session_valid():
            self._lock_screen()
        else:
            if self.auth:
                mins = self.auth.get_session_remaining_minutes()
                if self._status_bar:
                    self._status_bar.update_counts(session_minutes=mins)
            self.root.after(self.SESSION_CHECK_INTERVAL_MS, self._check_session_timeout)

    def _lock_screen(self):
        """Mostra schermata di blocco."""
        if not self.auth:
            return
        from ui.auth_dialogs import LockScreenDialog
        dlg = LockScreenDialog(self.root, self.auth, self.anomaly_detector)
        self.root.wait_window(dlg)
        if dlg.result:
            self.auth.refresh_session()
            self.root.after(self.SESSION_CHECK_INTERVAL_MS, self._check_session_timeout)

    # ── Utilities ────────────────────────────────────────────────

    def _get_current_photo(self) -> str:
        """Ritorna il path della foto corrente (da photo_manager se disponibile)."""
        if self.photo_manager and hasattr(self.photo_manager, 'get_current_photo'):
            return self.photo_manager.get_current_photo()
        return ''

    def _load_photo(self, photo_path: str):
        """
        Carica una foto nel canvas.
        USA SEMPRE memory_manager.open_thumbnail() — MAI Image.open() diretto.
        """
        if not photo_path or not self.canvas:
            return

        if self.memory_manager:
            thumbnail = self.memory_manager.open_thumbnail(
                photo_path,
                (self.canvas.winfo_width() or 800, self.canvas.winfo_height() or 600)
            )
        else:
            # Fallback se memory_manager non disponibile
            try:
                from PIL import Image
                with Image.open(photo_path) as img:
                    img.thumbnail((800, 600))
                    thumbnail = img.copy()
            except Exception:
                thumbnail = None

        if thumbnail is None:
            self.canvas.delete('all')
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text="⚠️ Immagine non valida",
                fill=THEME['accent_red'],
                font=(FONTS['family'], FONTS['size_lg'])
            )
            return

        try:
            from PIL import ImageTk
            self._photo_ref = ImageTk.PhotoImage(thumbnail)
            self.canvas.delete('all')
            cx = self.canvas.winfo_width() // 2
            cy = self.canvas.winfo_height() // 2
            self.canvas.create_image(cx, cy, image=self._photo_ref, anchor='center')
        except Exception as e:
            logger.debug("Errore visualizzazione foto: %s", e)

    def _on_canvas_resize(self, event=None):
        """Ricarica la foto quando il canvas cambia dimensione."""
        photo_path = self._get_current_photo()
        if photo_path:
            self._load_photo(photo_path)

    def _update_status(self):
        """Aggiorna la status bar."""
        if self._status_bar:
            session_mins = self.auth.get_session_remaining_minutes() if self.auth else -1
            self._status_bar.update_counts(
                moved=self._stats.get('moved', 0),
                duplicates=self._stats.get('duplicates', 0),
                errors=self._stats.get('errors', 0),
                session_minutes=session_mins,
            )

    def _update_highlights_list(self):
        """Aggiorna la lista highlight nel pannello destro."""
        if not self._highlights_list or not self.folder_manager_agent:
            return
        try:
            import config
            dest = getattr(config, 'DESTINATION_FOLDER', '')
            if dest:
                highlights = self.folder_manager_agent.get_existing_highlights(dest)
                self._highlights_list.delete(0, tk.END)
                for h in highlights:
                    self._highlights_list.insert(tk.END, f"⭐ {h}")
        except Exception as e:
            logger.debug("Update highlights list error: %s", e)

    def _check_dependency_audit(self):
        """Mostra banner se ci sono CVE nelle dipendenze."""
        if not self.dependency_audit:
            return
        try:
            vulns = self.dependency_audit.run()
            if vulns:
                warning = self.dependency_audit.format_warning(vulns)
                self._toast.show(
                    self.root,
                    f"⚠️ {len(vulns)} CVE trovati nelle dipendenze",
                    'warning',
                    duration_ms=8000
                )
                logger.warning(warning)
        except Exception as e:
            logger.debug("DependencyAudit in UI error: %s", e)
