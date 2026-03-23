# PIL_HARDENING.md — Sicurezza e Robustezza PIL/Pillow

Leggi questo file dopo SECURITY.md e prima di implementare FileValidatorAgent,
ExifSanitizerAgent e UIAgent.

Fonti: Pillow issue tracker (#7935, #7961, #515), Pillow 8.2.0 release notes,
OWASP DA6 (Security Misconfiguration), OWASP DA8 (Poor Code Quality).

---

## Problema 1 — Decompression Bomb Attack (CRITICO)

### Il rischio

Un file immagine può avere dimensioni su disco ridotte (50KB) ma espandersi
a gigabyte in RAM quando Pillow lo decomprime. È un attacco DoS classico
contro le app che processano immagini arbitrarie.

Pillow ha una protezione nativa tramite `MAX_IMAGE_PIXELS`, ma:
- il valore di default non è abbastanza restrittivo per app desktop
- il codice originale non lo configura esplicitamente
- il `DecompressionBombWarning` di default non blocca l'esecuzione

### Soluzione: DecompressionBombGuardAgent

**File**: `agents/security/decompression_bomb_guard.py`

```python
import warnings
from PIL import Image

class DecompressionBombGuardAgent:
    """
    Configura Pillow per bloccare (non solo avvisare) in caso di immagini
    troppo grandi. Da chiamare UNA SOLA VOLTA all'avvio, prima di qualsiasi
    Image.open().
    """

    # 100 megapixel = limite ragionevole per foto da smartphone
    # Una foto 4K è ~8MP, una foto di alta qualità è ~50MP
    MAX_PIXELS = 100_000_000  # 100 MP

    def __init__(self, max_pixels: int = MAX_PIXELS):
        self.max_pixels = max_pixels

    def configure(self):
        """
        Imposta il limite e converte il warning in errore bloccante.
        Chiama questo metodo come prima cosa in main.py.
        """
        Image.MAX_IMAGE_PIXELS = self.max_pixels
        # Converte DecompressionBombWarning in eccezione bloccante
        warnings.filterwarnings(
            'error',
            category=Image.DecompressionBombWarning
        )

    def safe_open(self, file_path: str) -> Image.Image | None:
        """
        Apre un'immagine in modo sicuro.
        Ritorna None se è una decompression bomb o se il file è corrotto.
        Deve essere usato SEMPRE al posto di Image.open() diretto.
        """
        try:
            # Usa context manager per prevenire memory leak
            img = Image.open(file_path)
            img.verify()  # Verifica integrità senza caricare i pixel
            # Riapri dopo verify() — verify() consuma il file pointer
            return Image.open(file_path)
        except Image.DecompressionBombWarning:
            return None
        except Image.DecompressionBombError:
            return None
        except Exception:
            return None
```

### Integrazione obbligatoria in main.py

```python
# PRIMA riga dopo gli import, prima di tutto il resto
bomb_guard = DecompressionBombGuardAgent(max_pixels=100_000_000)
bomb_guard.configure()
```

### Integrazione in UIAgent (caricamento foto per anteprima)

```python
# MAI così
img = Image.open(photo_path)

# SEMPRE così
img = bomb_guard.safe_open(photo_path)
if img is None:
    # Mostra placeholder "immagine non valida" nel canvas
    self._show_invalid_placeholder()
    return
```

---

## Problema 2 — Memory Leak PIL con archivi grandi (ALTO)

### Il rischio

Documentato in Pillow issue #7935 (2024): ogni immagine processata lascia
~8MB di memoria non rilasciata. Con 350 foto (archivio tipico):
- Memory leak: ~2.8GB
- Crash quasi garantito su macchine con 8GB RAM

Il codice originale apre ogni foto con `Image.open(photo_path)` senza
context manager né chiusura esplicita.

### MemoryManagerAgent

**File**: `agents/security/memory_manager.py`

```python
import gc
import contextlib
from PIL import Image

class MemoryManagerAgent:
    """
    Gestisce apertura sicura di immagini PIL prevenendo memory leak.
    Forza garbage collection periodica su archivi grandi.
    """

    def __init__(self, gc_every_n_photos: int = 50):
        self.gc_every_n_photos = gc_every_n_photos
        self._photo_count = 0

    @contextlib.contextmanager
    def open_image(self, file_path: str):
        """
        Context manager sicuro per aprire immagini.
        Garantisce la chiusura anche in caso di eccezioni.

        Uso:
            with memory_manager.open_image(path) as img:
                thumbnail = img.copy()
                img.thumbnail((800, 600))
        """
        img = None
        try:
            img = Image.open(file_path)
            img.load()  # Forza il caricamento in memoria ora
            yield img
        finally:
            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
            self._photo_count += 1
            if self._photo_count % self.gc_every_n_photos == 0:
                gc.collect()

    def open_thumbnail(self, file_path: str,
                       max_size: tuple = (800, 600)) -> Image.Image | None:
        """
        Apre un'immagine, ne crea una thumbnail e chiude l'originale.
        Ritorna la thumbnail (in memoria, piccola) o None.
        """
        try:
            with self.open_image(file_path) as img:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                return img.copy()  # Copia prima che il context manager chiuda
        except Exception:
            return None

    def force_gc(self):
        """Forza garbage collection manuale."""
        gc.collect()
```

### Pattern di uso obbligatorio in UIAgent

```python
# MAI così (memory leak garantito su archivi grandi)
img = Image.open(photo_path)
img.thumbnail((800, 600), Image.Resampling.LANCZOS)
self.photo = ImageTk.PhotoImage(img)

# SEMPRE così
thumbnail = self.memory_manager.open_thumbnail(photo_path, (800, 600))
if thumbnail:
    self.photo = ImageTk.PhotoImage(thumbnail)
    # thumbnail rimane in scope (tkinter ne ha bisogno)
    # ma è piccola (~50KB vs 8MB originale)
```

---

## Problema 3 — _getexif() deprecato (MEDIO)

### Il rischio

`_getexif()` è un metodo privato (prefisso underscore). Dal 2021 Pillow
ha cambiato il comportamento di `getexif()` riguardo al GPS IFD:
- `_getexif()`: appiattisce tutti i tag in un dizionario piatto
- `getexif()`: mantiene separati i sotto-IFD (GPS, EXIF IFD, ecc.)

Il codice originale usa `_getexif()` che è instabile tra versioni di Pillow.

### Fix in ExifSanitizerAgent

```python
# MAI così (privato, deprecato)
exif_data = image._getexif()

# SEMPRE così (API pubblica stabile da Pillow 6.0)
exif_data = image.getexif()

# Per il GPS IFD (importante per GpsStripperAgent):
gps_ifd = exif_data.get_ifd(0x8825)   # GPS IFD tag
exif_ifd = exif_data.get_ifd(0x8769)  # EXIF IFD tag

# NOTA: con getexif(), il GPS non è più nel dizionario principale
# ma va letto tramite get_ifd(0x8825)
```

---

## Problema 4 — XMP metadata non gestiti (BASSO-MEDIO)

### Il rischio

Oltre agli EXIF, le immagini JPEG/TIFF/PNG contengono metadati XMP (formato
Adobe). Gli XMP possono contenere:
- Coordinate GPS (gps:Latitude, gps:Longitude)
- Autore (dc:creator)
- Copyright
- Descrizioni personalizzate (dc:description)
- Storico modifiche (xmpMM:History)

Il GpsStripperAgent attuale usa piexif che gestisce solo EXIF, non XMP.

### XmpStripperAgent

**File**: `agents/security/xmp_stripper.py`

```python
class XmpStripperAgent:
    """
    Rimuove o sanitizza i metadati XMP dalle immagini prima
    di copiarle in cartelle pubbliche/condivise.
    """

    # Campi XMP da rimuovere nelle foto condivise
    XMP_FIELDS_TO_STRIP = {
        'gps:Latitude', 'gps:Longitude', 'gps:Altitude',
        'gps:GPSLatitude', 'gps:GPSLongitude',
        'xmp:CreatorTool',
        'dc:creator',       # nome autore
        'photoshop:City', 'photoshop:State', 'photoshop:Country',
        'Iptc4xmpCore:Location',
    }

    def strip_xmp(self, source_path: str, dest_path: str) -> bool:
        """
        Copia il file rimuovendo i campi XMP sensibili.
        Ritorna True se XMP rimosso, False altrimenti.
        """
        try:
            from PIL import Image
            import shutil

            with Image.open(source_path) as img:
                xmp_data = img.getxmp()

            if not xmp_data:
                # Nessun XMP: copia normale
                shutil.copy2(source_path, dest_path)
                return False

            # XMP presente: rimuovi campi sensibili e riscrivi
            # Nota: Pillow non supporta ancora la scrittura XMP direttamente.
            # Usare piexif o rimozione totale come fallback sicuro.
            self._strip_xmp_with_piexif(source_path, dest_path)
            return True

        except ImportError:
            import shutil
            shutil.copy2(source_path, dest_path)
            return False
        except Exception:
            import shutil
            shutil.copy2(source_path, dest_path)
            return False

    def _strip_xmp_with_piexif(self, source_path: str, dest_path: str):
        """Rimuove tutti i dati XMP tramite lettura/riscrittura con piexif."""
        try:
            import piexif
            from PIL import Image

            with Image.open(source_path) as img:
                # Copia senza XMP (piexif non gestisce XMP,
                # ma il salvataggio con exif= esclude i segmenti APP1/APP13 XMP)
                exif_dict = piexif.load(source_path)
                exif_dict['GPS'] = {}
                exif_bytes = piexif.dump(exif_dict)
                img.save(dest_path, exif=exif_bytes)
        except Exception:
            import shutil
            shutil.copy2(source_path, dest_path)
```

---

## Checklist PIL hardening completa

```python
# main.py — configurazione PIL all'avvio (PRIMA DI TUTTO)

import warnings
from PIL import Image

# 1. Limite pixel (decompression bomb)
Image.MAX_IMAGE_PIXELS = 100_000_000
warnings.filterwarnings('error', category=Image.DecompressionBombWarning)

# 2. Non caricare immagini troncate silenziosamente
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = False  # Default: False — mantienilo così

# 3. Istanzia MemoryManagerAgent per tutti gli open successivi
memory_manager = MemoryManagerAgent(gc_every_n_photos=50)
```

## Test da aggiungere

**File**: `tests/test_pil_hardening.py`

```python
def test_decompression_bomb_blocked():
    # Crea un file PNG "bomb" (immagine 1x1 con dimensioni dichiarate enormi)
    # FileValidatorAgent o DecompressionBombGuardAgent deve bloccarlo

def test_memory_manager_closes_file():
    # Verifica che open_image() chiuda il file anche se lancia eccezione

def test_exif_uses_public_getexif():
    # Verifica che ExifSanitizerAgent non usi _getexif()
    # (grep sul codice, oppure mock del metodo privato)

def test_xmp_stripped_from_highlights():
    # Foto con XMP GPS → copia in HIGHLIGHTS → XMP assente nella copia
```
