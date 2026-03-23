import os
from utils.file_utils import get_photo_date
from config import PROGRESS_FILE


class PhotoManager:
    """Gestisce le operazioni sulle foto"""

    def __init__(self, all_photos):
        self.all_photos = all_photos
        self.current_index = 0
        self.history = []
        self.stats = {
            'deleted': 0,
            'highlights': 0,
            'skipped': 0
        }
        self.processed_photos = set()  # Foto già processate

        # Carica progresso precedente se esiste
        self.load_progress()

    def load_progress(self):
        """Carica il progresso da file checkpoint"""
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                    # Prima riga: indice corrente
                    if lines:
                        self.current_index = int(lines[0].strip())

                    # Righe successive: foto già processate
                    for line in lines[1:]:
                        photo_path = line.strip()
                        if photo_path:
                            self.processed_photos.add(photo_path)

                print(f"✓ Progresso ripristinato: riprendi dalla foto {self.current_index + 1}/{len(self.all_photos)}")
                print(f"✓ Foto già processate: {len(self.processed_photos)}\n")

            except Exception as e:
                print(f"⚠️  Errore nel caricamento del progresso: {e}")
                self.current_index = 0
                self.processed_photos = set()

    def save_progress(self):
        """Salva il progresso corrente su file"""
        try:
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                # Salva indice corrente
                f.write(f"{self.current_index}\n")

                # Salva lista foto processate
                for photo_path in self.processed_photos:
                    f.write(f"{photo_path}\n")

        except Exception as e:
            print(f"⚠️  Errore nel salvataggio del progresso: {e}")

    def mark_as_processed(self, photo_path):
        """Segna una foto come processata"""
        self.processed_photos.add(photo_path)
        self.save_progress()

    def is_processed(self, photo_path):
        """Verifica se una foto è già stata processata"""
        return photo_path in self.processed_photos

    def clear_progress(self):
        """Cancella il file di progresso"""
        if os.path.exists(PROGRESS_FILE):
            try:
                os.remove(PROGRESS_FILE)
                print("✓ Progresso cancellato")
            except Exception as e:
                print(f"⚠️  Errore nella cancellazione del progresso: {e}")

    def get_current_photo(self):
        """Ottiene il percorso della foto corrente"""
        if self.current_index < len(self.all_photos):
            return self.all_photos[self.current_index]
        return None

    def get_current_photo_date(self):
        """Ottiene la data della foto corrente"""
        photo_path = self.get_current_photo()
        if photo_path:
            return get_photo_date(photo_path)
        return None

    def next_photo(self):
        """Passa alla foto successiva"""
        self.current_index += 1
        self.save_progress()

    def previous_photo(self):
        """Torna alla foto precedente"""
        if self.current_index > 0:
            self.current_index -= 1
            self.save_progress()

    def is_last_photo(self):
        """Verifica se siamo all'ultima foto"""
        return self.current_index >= len(self.all_photos)

    def get_progress(self):
        """Ottiene il progresso corrente"""
        return (self.current_index + 1, len(self.all_photos))

    def increment_stat(self, stat_name):
        """Incrementa una statistica"""
        if stat_name in self.stats:
            self.stats[stat_name] += 1

    def add_to_history(self, action, *args):
        """Aggiunge un'azione alla cronologia"""
        self.history.append((action, self.current_index, *args))