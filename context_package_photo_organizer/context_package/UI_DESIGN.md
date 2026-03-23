# UI_DESIGN.md — Design System e Specifiche Grafiche

Leggi questo file quando implementi UIAgent e auth_dialogs.py.
Sostituisce completamente il design attuale (Arial hardcoded, colori sparsi nel codice).

---

## Principi di design

1. **Consistenza**: un solo sistema di colori e font, definito in `config.py`
2. **Leggibilità**: foto al centro, controlli ai margini, info visibili ma non invasive
3. **Dark-first**: tema scuro come default (più comodo per guardare foto)
4. **Responsivo**: la finestra scala, non è fissa a 1400x900
5. **Feedback immediato**: ogni azione ha una risposta visiva (toast, progress, badge)

---

## Palette colori — Dark Theme (default)

```python
# In config.py — sostituisce il dizionario COLORS esistente

THEME = {
    # Sfondi
    'bg_primary':    '#0f1117',   # nero quasi puro — sfondo principale
    'bg_secondary':  '#1a1d27',   # blu-grigio scuro — pannelli
    'bg_tertiary':   '#252836',   # grigio-blu — card, input
    'bg_hover':      '#2e3148',   # hover su elementi interattivi

    # Accenti
    'accent_gold':   '#f5a623',   # oro — highlights, azioni primarie
    'accent_blue':   '#4a9eff',   # azzurro — navigazione, link
    'accent_green':  '#2ecc71',   # verde — successo, skip
    'accent_red':    '#e74c3c',   # rosso — delete, errori
    'accent_purple': '#9b59b6',   # viola — stampa, export

    # Testo
    'text_primary':  '#ffffff',   # bianco — titoli, label principali
    'text_secondary':'#a0aec0',   # grigio chiaro — label secondari, hint
    'text_muted':    '#4a5568',   # grigio scuro — disabilitato

    # Bordi
    'border':        '#2d3748',   # bordo sottile standard
    'border_focus':  '#4a9eff',   # bordo quando elemento ha focus

    # Speciali
    'overlay':       '#00000088', # overlay semitrasparente (lock screen)
    'shadow':        '#00000044', # ombra card
}

# Light theme (alternativo, attivabile da settings)
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
```

---

## Tipografia

```python
FONTS = {
    # Usa Segoe UI su Windows, SF Pro su macOS, Ubuntu su Linux
    'family':        'Segoe UI',
    'family_mono':   'Consolas',

    'size_xl':    18,   # titoli principali
    'size_lg':    14,   # header, bottoni grandi
    'size_md':    12,   # testo normale, label
    'size_sm':    10,   # hint, caption, badge
    'size_xs':     9,   # tooltip, note

    'weight_bold':   'bold',
    'weight_normal': 'normal',
}
```

Rileva la piattaforma e seleziona il font corretto:

```python
import platform
def get_system_font():
    system = platform.system()
    if system == 'Windows':
        return 'Segoe UI'
    elif system == 'Darwin':
        return 'SF Pro Display'
    else:
        return 'Ubuntu'
```

---

## Layout principale

```
┌────────────────────────────────────────────────────────────────────┐
│  HEADER (60px)                                                      │
│  [📸 Photo Organizer]   [Foto 42/350 ████████░░ 68%]   [⚙️] [🔒]  │
├──────────────────────────────────────────┬─────────────────────────┤
│                                          │  PANNELLO DESTRO (320px)│
│                                          │                         │
│           CANVAS FOTO                    │  ⭐ HIGHLIGHTS (scroll) │
│         (occupa tutto)                   │  ┌──────────────────┐   │
│                                          │  │ 1. Viaggio_JP(8) │   │
│                                          │  │ 2. Estate_24(12) │   │
│                                          │  │ ...              │   │
│                                          │  └──────────────────┘   │
│                                          │                         │
│                                          │  📅 MIGLIORI ANNO       │
│                                          │  [Genera raccolta]      │
├──────────────────────────────────────────┴─────────────────────────┤
│  INFO BAR (50px)                                                    │
│  📄 IMG_20240815.jpg   📅 15/08/2024   📁 EVENTI/2024_Estate       │
│  🔍 Nikon D750  📍 GPS rimosso  ✅ Originale (no duplicati)        │
├────────────────────────────────────────────────────────────────────┤
│  ACTION BAR (80px)                                                  │
│  [🗑️ Elimina]  [⏭️ Salta]  [⭐ Nuovo Highlight]  [⬅️ Indietro]    │
├────────────────────────────────────────────────────────────────────┤
│  STATUS BAR (24px)                                                  │
│  ✅ 42 organizzate  🔄 3 duplicate saltate  ⚠️ 1 errore  💾 Saved  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Componenti UI da implementare

### ProgressBar avanzata (header)

```python
# Non usare ttk.Progressbar standard — crea una custom con Canvas

class PhotoProgressBar(tk.Canvas):
    """
    Barra progresso con:
    - Percentuale numerica
    - Sfumatura colore (rosso → giallo → verde al crescere)
    - Animazione smooth su aggiornamento
    """
    def __init__(self, parent, total: int, **kwargs):
        super().__init__(parent, height=8, **kwargs)
        self.total = total
        self.current = 0

    def set_progress(self, current: int):
        self.current = current
        self._draw()

    def _draw(self):
        self.delete('all')
        w = self.winfo_width() or 200
        pct = self.current / max(self.total, 1)
        fill_w = int(w * pct)

        # Sfondo
        self.create_rectangle(0, 0, w, 8, fill=THEME['bg_tertiary'], outline='')

        # Barra colorata (verde se > 80%, giallo se > 40%, rosso altrimenti)
        if pct > 0.8:
            color = THEME['accent_green']
        elif pct > 0.4:
            color = THEME['accent_gold']
        else:
            color = THEME['accent_blue']

        if fill_w > 0:
            self.create_rectangle(0, 0, fill_w, 8, fill=color, outline='')
```

### Toast notification

```python
class ToastNotification:
    """
    Notifica temporanea non-invasiva (in basso a destra).
    Scompare automaticamente dopo N secondi.
    Tipi: success (verde), warning (giallo), error (rosso), info (blu)
    """
    def show(self, parent, message: str, type_: str = 'success', duration_ms: int = 2500):
        colors = {
            'success': THEME['accent_green'],
            'warning': THEME['accent_gold'],
            'error':   THEME['accent_red'],
            'info':    THEME['accent_blue'],
        }
        icons = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}
        ...
```

### ActionButton

```python
class ActionButton(tk.Frame):
    """
    Bottone con:
    - Icona grande (24px) + label + shortcut hint
    - Hover con animazione colore
    - Stato disabled visivo
    - Tooltip al passaggio del mouse
    """
    def __init__(self, parent, icon: str, label: str, shortcut: str,
                 command, color: str, **kwargs):
        ...
```

### HighlightCard

```python
class HighlightCard(tk.Frame):
    """
    Card per ogni highlight nel pannello destro:
    - Numero ordinale + nome + contatore foto (badge)
    - Sfondo colorato in base al tipo (recente = blu, normale = grigio)
    - Hover effect
    - Miniatura della prima foto (thumbnail 40x40px)
    """
    ...
```

### InfoBar

```python
# Sostituisce il Label info_label con una barra strutturata
# Mostra in modo visivo (con icone e badge colorati):
# - Nome file
# - Data scatto
# - Cartella destinazione
# - Info camera (se EXIF disponibile)
# - Badge "GPS rimosso" (verde) o "GPS presente" (arancione)
# - Badge "Originale" (verde) o "Duplicato di X" (rosso)
```

### StatusBar

```python
# Barra in fondo alla finestra (24px) sempre visibile
# Mostra in tempo reale:
# - Contatore foto organizzate (verde)
# - Contatore duplicati saltati (blu)
# - Contatore errori (rosso, visibile solo se > 0)
# - Indicatore "Salvato" o "In salvataggio..." (grigio/verde)
# - Indicatore sessione: "🔒 Sessione: 45 min rimanenti"
```

---

## Schermata di Login (PinSetupDialog / LoginDialog)

```
┌────────────────────────────────────────────────┐
│                                                │
│                   📸                           │
│           Photo Organizer                      │
│                                                │
│    ┌──────────────────────────────────────┐    │
│    │  PIN  ● ● ● ●  _                    │    │
│    └──────────────────────────────────────┘    │
│                                                │
│         [    Accedi    ]                       │
│                                                │
│    ⚠️ PIN errato. 2 tentativi rimanenti.       │
│                                                │
│              ? Reset PIN                       │
└────────────────────────────────────────────────┘
```

- Finestra centrata, dimensione fissa 400x350
- Sfondo `bg_primary`, card centrale `bg_secondary` con bordo arrotondata
- Campo PIN con font monospace, caratteri mostrati come `●`
- Bottone "Accedi" largo, colore `accent_gold`, hover più scuro
- Messaggio errore in rosso, animazione shake sul campo PIN
- Animazione "fade in" all'apertura

---

## Schermata di completamento

Sostituisce il testo bianco su sfondo scuro con una card animata:

```
┌────────────────────────────────────────────────┐
│                                                │
│  🎉  Tutto organizzato!                        │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  ⭐ 23   │  │  ✅ 180  │  │  🗑️ 12  │     │
│  │Highlights│  │Organizzate│  │Eliminate │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│                                                │
│  📅 Raccolte annuali generate:                 │
│     • 2022_best_12 (12 foto)                   │
│     • 2023_best_12 (12 foto)                   │
│     • 2024_best_12 (8 foto)                    │
│                                                │
│  [  📄 Apri Report  ]  [  🔒 Esci  ]           │
│                                                │
└────────────────────────────────────────────────┘
```

---

## Responsività

```python
# Dimensioni minime e comportamento al resize

MIN_WIDTH  = 1000
MIN_HEIGHT = 700
DEFAULT_WIDTH  = 1400
DEFAULT_HEIGHT = 900

# Il canvas foto scala con la finestra
# Il pannello destro ha larghezza fissa (320px) ma altezza variabile
# Le action bar hanno altezza fissa
# La barra progresso nell'header si estende orizzontalmente
```

---

## Accessibilità

- Tutti i bottoni devono avere `tooltip` con descrizione azione + shortcut
- Contrasto testo/sfondo minimo 4.5:1 (WCAG AA)
- Focus visibile su tutti gli elementi interattivi (bordo `border_focus`)
- Tasti freccia per navigare tra i bottoni dell'action bar
- `Ctrl+Z` per undo dell'ultima azione (torna indietro)

---

## Animazioni (opzionali ma raccomandate)

Tutte tramite `root.after()` — nessuna libreria esterna:

- **Fade in** del canvas quando cambia foto (opacity 0→1 in 150ms)
- **Shake** del campo PIN al login fallito
- **Pulse** del badge contatore highlights quando viene aggiunto uno nuovo
- **Slide in** dei toast notification dal basso destra
- **Smooth update** della progress bar (incremento graduale in 200ms)
