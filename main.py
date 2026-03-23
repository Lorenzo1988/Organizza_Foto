#!/usr/bin/env python3
"""
Photo Organizer - Highlights Edition
Organizza le tue foto in modo intelligente con un'interfaccia grafica
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

from config import SOURCE_FOLDER, DESTINATION_FOLDER
from core.event_manager import EventManager
from core.folder_manager import FolderManager
from core.photo_manager import PhotoManager
from utils.date_utils import generate_easter_dates
from utils.file_utils import load_all_photos, get_photo_date
from ui.main_window import MainWindow


def organize_all_photos_first(all_photos, folder_manager):
    """
    FASE 1: Organizza TUTTE le foto in EVENTI/ARCHIVIO prima di avviare la GUI
    """
    print("=" * 70)
    print("FASE 1: ORGANIZZAZIONE AUTOMATICA")
    print("=" * 70)
    print(f"📂 Sposto tutte le {len(all_photos)} foto in EVENTI/ARCHIVIO...\n")

    organized_photos = []
    errors = 0

    for idx, photo_path in enumerate(all_photos, 1):
        try:
            photo_date = get_photo_date(photo_path)
            new_path = folder_manager.organize_to_default(photo_path, photo_date)
            organized_photos.append(new_path)

            if idx % 10 == 0 or idx == len(all_photos):
                print(f"✓ Organizzate: {idx}/{len(all_photos)}", end='\r')

        except Exception as e:
            print(f"\n⚠️  Errore con {os.path.basename(photo_path)}: {e}")
            errors += 1

    print()  # Newline dopo progress
    print("\n" + "=" * 70)
    print(f"✅ Fase 1 completata!")
    print(f"   • Foto organizzate: {len(organized_photos)}")
    print(f"   • Errori: {errors}")
    print("=" * 70)
    print()

    return organized_photos


def main():
    """Entry point dell'applicazione"""

    print("=" * 70)
    print("📸 PHOTO ORGANIZER - HIGHLIGHTS EDITION")
    print("=" * 70)
    print()

    # Carica eventi
    print("📅 Caricamento eventi...")
    event_manager = EventManager()
    print(f"✓ Eventi ricorrenti: {len(event_manager.events['recurring'])}")
    print(f"✓ Eventi puntuali: {len(event_manager.events['one_time'])}\n")

    # Genera date Pasqua
    print("🐣 Calcolo date di Pasqua 2000-2050...")
    easter_dates = generate_easter_dates()
    print("✓ Date calcolate\n")

    # Inizializza folder manager
    folder_manager = FolderManager(DESTINATION_FOLDER, event_manager, easter_dates)

    # SCELTA INIZIALE: Checkpoint o nuove foto?
    from config import PROGRESS_FILE
    checkpoint_exists = os.path.exists(PROGRESS_FILE)

    mode = None  # 'continue' o 'new'

    if checkpoint_exists:
        print("=" * 70)
        print("💾 CHECKPOINT TROVATO!")
        print("=" * 70)
        print("Cosa vuoi fare?\n")
        print("  [1] Continuare dal checkpoint (riprendi dove eri rimasto)")
        print("  [2] Organizzare un nuovo insieme di foto (cancella checkpoint)")

        while mode is None:
            choice = input("\nScelta (1/2): ").strip()

            if choice == '1':
                mode = 'continue'
                print("\n✓ Riprendo dalla sessione precedente\n")
            elif choice == '2':
                mode = 'new'
                os.remove(PROGRESS_FILE)
                print("\n✓ Checkpoint cancellato, organizzo nuove foto\n")
            else:
                print("⚠️  Scelta non valida, inserisci 1 o 2")
    else:
        # Nessun checkpoint, modalità nuova
        mode = 'new'
        print("📂 Nessun checkpoint trovato, organizzo nuove foto\n")

    # Esegui in base alla modalità scelta
    if mode == 'continue':
        # MODALITÀ CONTINUE: Carica foto da EVENTI/ARCHIVIO
        print(f"📂 Carico foto già organizzate da: {DESTINATION_FOLDER}")

        events_folder = os.path.join(DESTINATION_FOLDER, "📅 EVENTI")
        archive_folder = os.path.join(DESTINATION_FOLDER, "📸 ARCHIVIO")

        all_photos = []
        for folder in [events_folder, archive_folder]:
            if os.path.exists(folder):
                all_photos.extend(load_all_photos(folder))

        if not all_photos:
            print("❌ Nessuna foto trovata in EVENTI/ARCHIVIO!")
            print("   Sembra che il checkpoint sia corrotto.")
            if os.path.exists(PROGRESS_FILE):
                os.remove(PROGRESS_FILE)
            input("\nPremi Invio per uscire...")
            sys.exit(1)

        print(f"✓ Trovate {len(all_photos)} foto già organizzate\n")
        organized_photos = all_photos

    else:  # mode == 'new'
        # MODALITÀ NEW: Carica foto da SOURCE e organizza
        if not os.path.exists(SOURCE_FOLDER):
            print(f"❌ Errore: La cartella {SOURCE_FOLDER} non esiste!")
            print("\n💡 Modifica il file config.py con i percorsi corretti")
            input("\nPremi Invio per uscire...")
            sys.exit(1)

        print(f"📂 Scansione cartella sorgente: {SOURCE_FOLDER}")
        all_photos = load_all_photos(SOURCE_FOLDER)

        if not all_photos:
            print("⚠️  Nessuna foto trovata nella cartella sorgente!")
            input("\nPremi Invio per uscire...")
            sys.exit(0)

        print(f"✓ Trovate {len(all_photos)} foto\n")

        # FASE 1: Organizza TUTTE le foto automaticamente
        organized_photos = organize_all_photos_first(all_photos, folder_manager)

        if not organized_photos:
            print("❌ Nessuna foto è stata organizzata!")
            input("\nPremi Invio per uscire...")
            sys.exit(1)

    # FASE 2: GUI per scegliere highlights (comune per entrambe le modalità)
    print("=" * 70)
    print("FASE 2: SELEZIONE HIGHLIGHTS")
    print("=" * 70)
    print("Ora puoi scegliere quali foto promuovere a HIGHLIGHTS")
    print()

    # Inizializza photo manager con le foto GIÀ ORGANIZZATE
    photo_manager = PhotoManager(organized_photos)

    # Avvia GUI
    print("🚀 Avvio interfaccia grafica...\n")
    print("=" * 70)
    print("SCORCIATOIE DA TASTIERA:")
    print("  Spazio/→   = Salta (lascia in EVENTI/ARCHIVIO)")
    print("  H          = Crea nuovo highlight")
    print("  0-9        = Digita numero highlight (aspetta 2 sec)")
    print("               Es: 15 = aspetta 2 sec → highlight #15")
    print("  Canc/D     = Elimina foto")
    print("  ←          = Torna indietro")
    print("  Esc        = Chiudi programma")
    print("=" * 70)
    print("💾 Il progresso viene salvato automaticamente")
    print("   Puoi chiudere e riprendere quando vuoi!")
    print("=" * 70)
    print()

    try:
        root = tk.Tk()
        app = MainWindow(root, photo_manager, folder_manager)
        root.mainloop()

        print("\n✅ Programma terminato correttamente")
        print("💾 Progresso salvato - riprendi quando vuoi!")

    except Exception as e:
        print(f"\n❌ Errore durante l'esecuzione: {e}")
        import traceback
        traceback.print_exc()
        input("\nPremi Invio per uscire...")
        sys.exit(1)

1
if __name__ == "__main__":
    main()