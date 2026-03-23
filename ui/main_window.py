import os
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk

from config import COLORS
from ui.components import (
    create_styled_button, create_header,
    create_info_panel, create_canvas
)


class MainWindow:
    """Finestra principale dell'applicazione"""

    def __init__(self, root, photo_manager, folder_manager):
        self.root = root
        self.photo_manager = photo_manager
        self.folder_manager = folder_manager

        self.root.title("📸 Photo Organizer - Highlights Edition")
        self.root.geometry("1400x900")

        self.photo = None  # Reference per PhotoImage

        # Per gestire input a 2 cifre
        self.number_input = ""
        self.number_timer = None

        # Lista per highlights da spostare in fondo
        self.highlights_to_move_bottom = set()

        # Traccia gli ultimi 5 highlights usati
        self.recent_highlights = []  # Lista ordinata: il più recente è il primo

        self.setup_ui()
        self.setup_keyboard_shortcuts()
        self.load_current_photo()

    def setup_ui(self):
        """Configura l'interfaccia utente"""
        # Header
        self.progress_label = create_header(self.root)

        # Frame principale con contenuto centrale e pannello laterale
        content_frame = tk.Frame(self.root, bg=COLORS['main_bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Frame centrale (canvas + info + bottoni azione)
        center_frame = tk.Frame(content_frame, bg=COLORS['main_bg'])
        center_frame.pack(side='left', fill='both', expand=True)

        # Canvas per immagine
        self.canvas = create_canvas(center_frame)

        # Info panel
        self.info_label = create_info_panel(self.root)

        # Action buttons
        self.create_action_buttons()

        # Highlights panel A DESTRA
        self.create_highlights_panel(content_frame)

    def create_action_buttons(self):
        """Crea i pulsanti di azione principali"""
        action_frame = tk.Frame(self.root, bg=COLORS['main_bg'], height=100)
        action_frame.pack(fill='x', side='top')
        action_frame.pack_propagate(False)

        pack_opts = {'side': 'left', 'padx': 10, 'pady': 20, 'fill': 'x', 'expand': True}

        self.btn_delete = create_styled_button(
            action_frame,
            "🗑️ Elimina (Canc/D)",
            self.delete_photo,
            COLORS['delete_btn'],
            COLORS['delete_btn_active']
        )
        self.btn_delete.pack(**pack_opts)

        self.btn_skip = create_styled_button(
            action_frame,
            "⏭️ Salta (Spazio/→)",
            self.skip_photo,
            COLORS['skip_btn'],
            COLORS['skip_btn_active']
        )
        self.btn_skip.pack(**pack_opts)

        self.btn_new_highlight = create_styled_button(
            action_frame,
            "⭐ Nuovo Highlight (H)",
            self.create_new_highlight,
            COLORS['highlight_btn'],
            COLORS['highlight_btn_active']
        )
        self.btn_new_highlight.pack(**pack_opts)

        self.btn_back = create_styled_button(
            action_frame,
            "⬅️ Indietro (←)",
            self.go_back,
            COLORS['back_btn'],
            COLORS['back_btn_active']
        )
        self.btn_back.pack(**pack_opts)

    def create_highlights_panel(self, parent):
        """Crea il pannello degli highlights esistenti A DESTRA"""
        # Frame laterale destro con larghezza fissa
        right_panel = tk.Frame(parent, bg=COLORS['main_bg'], width=350)
        right_panel.pack(side='right', fill='y', padx=(20, 0))
        right_panel.pack_propagate(False)

        # Titolo
        title_label = tk.Label(
            right_panel,
            text="⭐ Highlights Esistenti",
            font=('Arial', 12, 'bold'),
            bg=COLORS['main_bg'],
            fg=COLORS['info_fg']
        )
        title_label.pack(anchor='w', pady=(0, 5))

        # Istruzioni
        instructions = tk.Label(
            right_panel,
            text="(Click o digita numero)",
            font=('Arial', 9),
            bg=COLORS['main_bg'],
            fg='#7f8c8d'
        )
        instructions.pack(anchor='w', pady=(0, 10))

        # Pulsante per gestire spostamento in fondo
        self.btn_manage_order = create_styled_button(
            right_panel,
            "📌 Gestisci Ordine",
            self.toggle_order_management,
            '#3498db',
            '#2980b9'
        )
        self.btn_manage_order.pack(fill='x', pady=(0, 10))

        # Frame con scrollbar per gli highlights
        scrollable_frame = tk.Frame(right_panel, bg=COLORS['main_bg'])
        scrollable_frame.pack(fill='both', expand=True)

        # Canvas per scrolling
        self.highlights_canvas = tk.Canvas(
            scrollable_frame,
            bg=COLORS['main_bg'],
            highlightthickness=0
        )
        self.highlights_canvas.pack(side='left', fill='both', expand=True)

        # Scrollbar
        scrollbar = tk.Scrollbar(
            scrollable_frame,
            orient='vertical',
            command=self.highlights_canvas.yview
        )
        scrollbar.pack(side='right', fill='y')

        self.highlights_canvas.configure(yscrollcommand=scrollbar.set)

        # Frame interno per i bottoni
        self.highlights_container = tk.Frame(self.highlights_canvas, bg=COLORS['main_bg'])
        self.canvas_window = self.highlights_canvas.create_window(
            (0, 0),
            window=self.highlights_container,
            anchor='nw'
        )

        # Bind per aggiornare scrollregion
        self.highlights_container.bind(
            '<Configure>',
            lambda e: self.highlights_canvas.configure(scrollregion=self.highlights_canvas.bbox('all'))
        )

        # Bind per scroll con mousewheel
        self.highlights_canvas.bind('<Enter>', self._bind_mousewheel)
        self.highlights_canvas.bind('<Leave>', self._unbind_mousewheel)

        # Flag per modalità gestione ordine
        self.order_management_mode = False

        self.update_highlights_buttons()

    def _bind_mousewheel(self, event):
        """Abilita scroll con rotella mouse"""
        self.highlights_canvas.bind_all('<MouseWheel>', self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        """Disabilita scroll con rotella mouse"""
        self.highlights_canvas.unbind_all('<MouseWheel>')

    def _on_mousewheel(self, event):
        """Gestisce scroll con rotella mouse"""
        self.highlights_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def toggle_order_management(self):
        """Attiva/disattiva modalità gestione ordine"""
        self.order_management_mode = not self.order_management_mode

        if self.order_management_mode:
            self.btn_manage_order.config(
                text="✅ Conferma Selezione",
                bg='#27ae60',
                activebackground='#229954'
            )
            messagebox.showinfo(
                "Modalità Gestione Ordine",
                "Clicca sugli highlights che vuoi spostare in fondo.\n"
                "Clicca di nuovo per confermare la selezione."
            )
        else:
            # Applica lo spostamento
            if self.highlights_to_move_bottom:
                messagebox.showinfo(
                    "Ordine Aggiornato",
                    f"{len(self.highlights_to_move_bottom)} highlight(s) spostati in fondo alla lista."
                )
            self.btn_manage_order.config(
                text="📌 Gestisci Ordine",
                bg='#3498db',
                activebackground='#2980b9'
            )

        self.update_highlights_buttons()

    def update_highlights_buttons(self):
        """Aggiorna i bottoni degli highlights esistenti con ultimi 5 usati in alto"""
        for widget in self.highlights_container.winfo_children():
            widget.destroy()

        highlights = self.folder_manager.get_existing_highlights()

        if not highlights:
            tk.Label(
                self.highlights_container,
                text="Nessun highlight creato ancora",
                font=('Arial', 10),
                fg='#7f8c8d',
                bg=COLORS['main_bg']
            ).pack(anchor='w', pady=10)
            return

        # DEBUG: stampa per vedere cosa c'è in recent_highlights
        print(f"DEBUG - recent_highlights: {self.recent_highlights}")
        print(f"DEBUG - all highlights: {highlights}")

        # Ordina alfabeticamente
        sorted_highlights = sorted(highlights, key=lambda x: x.lower())

        # Separa highlights recenti (ultimi 5 usati)
        recent_in_list = [h for h in self.recent_highlights if h in sorted_highlights][:5]

        print(f"DEBUG - recent_in_list: {recent_in_list}")

        # Separa highlights normali (esclusi i recenti e quelli da spostare in fondo)
        normal_highlights = [
            h for h in sorted_highlights
            if h not in recent_in_list and h not in self.highlights_to_move_bottom
        ]

        # Separa highlights da spostare in fondo
        bottom_highlights = [h for h in sorted_highlights if h in self.highlights_to_move_bottom]

        # Combina le liste: recenti → normali → in fondo
        ordered_highlights = recent_in_list + normal_highlights + bottom_highlights

        print(f"DEBUG - ordered_highlights: {ordered_highlights}")

        # Crea i bottoni
        for idx, highlight in enumerate(ordered_highlights, 1):
            is_recent = highlight in recent_in_list
            is_bottom = highlight in self.highlights_to_move_bottom

            # Conta il numero di foto nell'highlight
            photo_count = self.folder_manager.count_photos_in_highlight(highlight)

            # Determina il colore
            if self.order_management_mode and is_bottom:
                btn_color = '#e67e22'  # Arancione per selezionati in modalità gestione
                btn_active_color = '#d35400'
            elif is_bottom:
                btn_color = '#95a5a6'  # Grigio per quelli in fondo
                btn_active_color = '#7f8c8d'
            elif is_recent:
                btn_color = '#3498db'  # Azzurro più scuro per i recenti (primi 5)
                btn_active_color = '#2980b9'
            else:
                btn_color = '#85c1e9'  # Azzurro pastello chiaro per gli altri
                btn_active_color = '#5dade2'

            btn = tk.Button(
                self.highlights_container,
                text=f"{idx}. {highlight} ({photo_count})",
                command=lambda h=highlight: self.handle_highlight_click(h),
                bg=btn_color,
                fg='white',
                font=('Arial', 9),
                cursor='hand2',
                relief='raised',
                padx=10,
                pady=5,
                anchor='w',
                wraplength=300
            )
            btn.pack(fill='x', padx=5, pady=2)

    def handle_highlight_click(self, highlight_name):
        """Gestisce il click su un highlight (normale o gestione ordine)"""
        if self.order_management_mode:
            # Modalità gestione: aggiungi/rimuovi dalla lista da spostare
            if highlight_name in self.highlights_to_move_bottom:
                self.highlights_to_move_bottom.remove(highlight_name)
            else:
                self.highlights_to_move_bottom.add(highlight_name)
            self.update_highlights_buttons()
        else:
            # Modalità normale: sposta foto
            self.move_to_highlight_with_print_prompt(highlight_name)

    def setup_keyboard_shortcuts(self):
        """Configura le scorciatoie da tastiera"""
        self.root.bind('<Delete>', lambda e: self.delete_photo())
        self.root.bind('d', lambda e: self.delete_photo())
        self.root.bind('h', lambda e: self.create_new_highlight())
        self.root.bind('<space>', lambda e: self.skip_photo())
        self.root.bind('<Right>', lambda e: self.skip_photo())
        self.root.bind('<Left>', lambda e: self.go_back())
        self.root.bind('<Escape>', lambda e: self.root.quit())

        # Bind numeri 0-9 per input multi-cifra
        for i in range(10):
            self.root.bind(str(i), lambda e, digit=i: self.handle_number_input(digit))

    def handle_number_input(self, digit):
        """Gestisce input numerico multi-cifra con timeout di 1 secondo"""
        # Aggiungi la cifra all'input
        self.number_input += str(digit)

        # Cancella il timer precedente se esiste
        if self.number_timer:
            self.root.after_cancel(self.number_timer)

        # Mostra il numero nell'header temporaneamente
        current, total = self.photo_manager.get_progress()
        self.progress_label.config(
            text=f"📸 Foto {current} / {total} | Numero digitato: {self.number_input}"
        )

        # Imposta un timer di 1 secondo
        self.number_timer = self.root.after(1000, self.process_number_input)

    def process_number_input(self):
        """Processa il numero dopo 1 secondo di timeout"""
        if self.number_input:
            try:
                number = int(self.number_input)
                self.quick_move_to_highlight(number - 1)  # -1 perché array parte da 0
            except ValueError:
                pass

            # Reset
            self.number_input = ""

            # Ripristina l'header normale
            current, total = self.photo_manager.get_progress()
            self.progress_label.config(text=f"📸 Foto {current} / {total}")

    def move_to_highlight_with_print_prompt(self, highlight_name):
        """Wrapper per chiedere se stampare prima di spostare in highlight"""
        add_to_print = messagebox.askyesno(
            "Da Stampare?",
            "Vuoi aggiungere questa foto anche a 'Da Stampare'?"
        )
        self.move_to_highlight(highlight_name, add_to_print=add_to_print)

    def load_current_photo(self):
        """Carica e visualizza la foto corrente"""
        if self.photo_manager.is_last_photo():
            self.show_completion()
            return

        photo_path = self.photo_manager.get_current_photo()
        current, total = self.photo_manager.get_progress()

        self.progress_label.config(text=f"📸 Foto {current} / {total}")

        try:
            img = Image.open(photo_path)

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 800
                canvas_height = 600

            img.thumbnail((canvas_width - 40, canvas_height - 40), Image.Resampling.LANCZOS)

            self.photo = ImageTk.PhotoImage(img)

            self.canvas.delete("all")
            x = (canvas_width - self.photo.width()) // 2
            y = (canvas_height - self.photo.height()) // 2
            self.canvas.create_image(x, y, anchor='nw', image=self.photo)

            # Aggiorna info
            self.update_photo_info(photo_path)

        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare l'immagine:\n{e}")
            self.skip_photo()

    def update_photo_info(self, photo_path):
        """Aggiorna le informazioni della foto"""
        photo_date = self.photo_manager.get_current_photo_date()
        filename = os.path.basename(photo_path)
        folder_name, priority = self.folder_manager.determine_folder(photo_date)

        if priority >= 3:
            default_location = f"EVENTI/{folder_name}"
        else:
            default_location = f"ARCHIVIO/{folder_name}"

        info_text = f"📄 {filename}\n"
        info_text += f"📅 Data: {photo_date.strftime('%d/%m/%Y')}\n"
        info_text += f"📁 Posizione attuale: {default_location}"

        self.info_label.config(text=info_text)

    def delete_photo(self):
        """Elimina la foto corrente (da EVENTI/ARCHIVIO)"""
        if messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare questa foto?"):
            photo_path = self.photo_manager.get_current_photo()
            try:
                os.remove(photo_path)

                # Segna come processata
                self.photo_manager.mark_as_processed(photo_path)

                self.photo_manager.increment_stat('deleted')
                self.photo_manager.add_to_history('delete')
                self.next_photo()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile eliminare la foto:\n{e}")

    def skip_photo(self):
        """Salta la foto (resta in EVENTI/ARCHIVIO)"""
        photo_path = self.photo_manager.get_current_photo()

        # Segna come processata
        self.photo_manager.mark_as_processed(photo_path)

        self.photo_manager.increment_stat('skipped')
        self.photo_manager.add_to_history('skip')
        self.next_photo()

    def create_new_highlight(self):
        """Crea una nuova cartella highlight"""
        name = simpledialog.askstring(
            "Nuovo Highlight",
            "Nome del nuovo highlight:\n(es: Viaggio_Giappone, Matrimonio_Mario)",
            parent=self.root
        )

        if name:
            name = name.strip().replace('/', '_').replace('\\', '_')
            if name:
                # Chiedi se aggiungere a "Da Stampare"
                add_to_print = messagebox.askyesno(
                    "Da Stampare?",
                    "Vuoi aggiungere questa foto anche a 'Da Stampare'?"
                )
                self.move_to_highlight(name, is_new=True, add_to_print=add_to_print)

    def move_to_highlight(self, highlight_name, is_new=False, add_to_print=False):
        """Sposta la foto corrente in un highlight"""
        photo_path = self.photo_manager.get_current_photo()
        photo_date = self.photo_manager.get_current_photo_date()

        try:
            self.folder_manager.move_to_highlight(photo_path, photo_date, highlight_name, add_to_print)

            # Segna come processata
            self.photo_manager.mark_as_processed(photo_path)

            self.photo_manager.increment_stat('highlights')
            self.photo_manager.add_to_history('highlight', highlight_name)

            # Aggiorna la lista degli ultimi 5 highlights usati
            if highlight_name in self.recent_highlights:
                # Rimuovi se già presente per spostarlo in cima
                self.recent_highlights.remove(highlight_name)
            self.recent_highlights.insert(0, highlight_name)  # Aggiungi in cima

            # Mantieni solo gli ultimi 5
            if len(self.recent_highlights) > 5:
                self.recent_highlights = self.recent_highlights[:5]

            # SEMPRE aggiorna i bottoni per mostrare il nuovo conteggio e ordine
            self.update_highlights_buttons()

            self.next_photo()

        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile copiare la foto:\n{e}")

    def quick_move_to_highlight(self, index):
        """Sposta velocemente usando tasti numerici"""
        highlights = self.folder_manager.get_existing_highlights()

        # Ordina come nella visualizzazione
        sorted_highlights = sorted(highlights, key=lambda x: x.lower())

        # Ricostruisci l'ordine come nella UI
        recent_in_list = [h for h in self.recent_highlights if h in sorted_highlights][:5]
        normal_highlights = [
            h for h in sorted_highlights
            if h not in recent_in_list and h not in self.highlights_to_move_bottom
        ]
        bottom_highlights = [h for h in sorted_highlights if h in self.highlights_to_move_bottom]
        ordered_highlights = recent_in_list + normal_highlights + bottom_highlights

        if 0 <= index < len(ordered_highlights):
            # Chiedi se aggiungere a "Da Stampare"
            add_to_print = messagebox.askyesno(
                "Da Stampare?",
                "Vuoi aggiungere questa foto anche a 'Da Stampare'?"
            )
            self.move_to_highlight(ordered_highlights[index], add_to_print=add_to_print)
        else:
            messagebox.showinfo("Info", f"Highlight numero {index + 1} non esiste!")
            # Reset input number
            self.number_input = ""
            current, total = self.photo_manager.get_progress()
            self.progress_label.config(text=f"📸 Foto {current} / {total}")

    def go_back(self):
        """Torna alla foto precedente"""
        if self.photo_manager.current_index > 0:
            self.photo_manager.previous_photo()
            self.load_current_photo()
        else:
            messagebox.showinfo("Info", "Sei già alla prima foto!")

    def next_photo(self):
        """Passa alla foto successiva"""
        self.photo_manager.next_photo()
        self.load_current_photo()

    def show_completion(self):
        """Mostra schermata di completamento"""
        self.canvas.delete("all")

        stats = self.photo_manager.stats
        completion_text = f"""
        🎉 COMPLETATO! 🎉

        ⭐ Foto promosse a highlights: {stats['highlights']}
        ✅ Foto lasciate in EVENTI/ARCHIVIO: {stats['skipped']}
        🗑️ Foto eliminate: {stats['deleted']}

        📁 Organizzazione finale:

        ⭐ HIGHLIGHTS - Le foto migliori (copiate qui)
        📅 EVENTI - Eventi e ricorrenze
        📸 ARCHIVIO - Tutto il resto per mese

        💾 Progresso salvato automaticamente
        """

        self.canvas.create_text(
            600, 300,
            text=completion_text,
            font=('Arial', 16),
            fill='white',
            justify='center'
        )

        # Disabilita pulsanti
        self.btn_delete.config(state='disabled')
        self.btn_skip.config(state='disabled')
        self.btn_new_highlight.config(state='disabled')
        self.btn_back.config(state='disabled')

        # Cancella il checkpoint alla fine
        self.photo_manager.clear_progress()