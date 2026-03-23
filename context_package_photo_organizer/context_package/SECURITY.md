# SECURITY.md — Specifiche di Sicurezza

## Vulnerabilità identificate nel codice originale

Queste vulnerabilità sono state trovate analizzando il codice esistente.
Ogni agente del Security Gate è progettato per mitigarne una specifica.

---

### 1. Path Traversal — `folder_manager.py:107`

**Problema**: il parametro `highlight_name` proviene dall'input utente nella GUI
e viene usato direttamente in `os.path.join` senza validazione:

```python
# CODICE ORIGINALE VULNERABILE
highlight_path = os.path.join(self.highlights_folder, highlight_name)
```

Un utente potrebbe digitare `../../Windows/System32` come nome highlight,
causando la scrittura di file fuori dalla cartella di destinazione.

**Mitigazione**: `PathGuardAgent.validate_highlight_name()` + `safe_join()`.

```python
# CODICE SICURO
clean_name = self.path_guard.validate_highlight_name(highlight_name)
highlight_path = self.path_guard.safe_join(self.highlights_folder, clean_name)
```

---

### 2. EXIF Injection — `file_utils.py:70`

**Problema**: i metadati EXIF vengono letti e usati senza sanitizzazione.
Un file immagine modificato potrebbe contenere stringhe arbitrariamente lunghe
o caratteri speciali nel campo `DateTimeOriginal` o in altri tag.

```python
# CODICE ORIGINALE VULNERABILE
image = Image.open(file_path)
exif_data = image._getexif()
# tutti i tag usati direttamente senza whitelist
```

**Mitigazione**: `ExifSanitizerAgent` usa una whitelist di tag e sanitizza
i valori accettando solo tipi primitivi con lunghezza massima.

---

### 3. File Masquerading — `file_utils.py:17`

**Problema**: il codice verifica solo l'estensione del filename:

```python
# CODICE ORIGINALE VULNERABILE
file_ext = Path(filename).suffix.lower()
if file_ext in PHOTO_EXTENSIONS:
    photos.append(file_path)
```

Un eseguibile rinominato `.jpg` supererebbe questo controllo.

**Mitigazione**: `FileValidatorAgent` legge i primi 16 byte del file
e li confronta con le magic signatures note delle immagini.

---

### 4. Move senza backup — `folder_manager.py:93`

**Problema**: `shutil.move` è irreversibile. Se il processo si interrompe
a metà (crash, corrente), le foto possono risultare né in source né in destination.

```python
# CODICE ORIGINALE
shutil.move(photo_path, dest_path)
```

**Mitigazione**: `FolderManagerAgent` usa una strategia copy-then-delete:
1. Copia il file nella destinazione
2. Verifica l'integrità (hash MD5 source == hash MD5 dest)
3. Solo se verificata, elimina il file sorgente
4. Logga ogni step sull'AuditLogger

```python
# CODICE SICURO
shutil.copy2(src, dst)
if md5(src) == md5(dst):
    audit_logger.log_delete(src)
    os.remove(src)
else:
    raise IOError("Verifica integrità fallita dopo la copia")
```

---

### 5. Checkpoint Injection — `photo_manager.py:27`

**Problema**: il file `progress_checkpoint.txt` viene letto e i percorsi
delle foto vengono usati direttamente senza validazione:

```python
# CODICE ORIGINALE VULNERABILE
for line in lines[1:]:
    photo_path = line.strip()
    self.processed_photos.add(photo_path)  # path non validato
```

Un checkpoint manomesso potrebbe far processare percorsi arbitrari.

**Mitigazione**: `CheckpointManagerAgent` valida ogni percorso letto
dal checkpoint usando `PathGuardAgent.is_safe_path()` prima di aggiungerlo.

---

### 6. Assenza di Audit Trail

**Problema**: nessuna operazione di move/copy/delete viene loggata.
In caso di perdita di foto non c'è modo di ricostruire cosa è successo.

**Mitigazione**: `AuditLoggerAgent` apre il file in modalità append-only
e scrive ogni operazione con timestamp ISO, path sorgente, path destinazione
e hash MD5 del file (calcolato sul sorgente prima dell'operazione).

---

## Regole di sicurezza da rispettare nel codice

### PathGuard: usalo SEMPRE per costruire path

```python
# MAI così
dest = os.path.join(base_folder, user_input, filename)

# SEMPRE così
dest = path_guard.safe_join(base_folder, user_input, filename)
```

### AuditLogger: logga PRIMA dell'operazione

```python
# MAI così
shutil.move(src, dst)
audit_logger.log_move(src, dst)  # se move crashasse, il log sarebbe perso

# SEMPRE così
audit_logger.log_move(src, dst)   # prima
shutil.move(src, dst)             # poi
```

### FileValidator: fallire in modo sicuro

```python
# Il validator deve ritornare False, non lanciare eccezioni
# L'Orchestratore controlla il valore di ritorno e skippa il file
if not file_validator.validate(file_path):
    audit_logger.log_skip(file_path, file_validator.get_errors())
    continue
```

### ExifSanitizer: mai usare _getexif() direttamente

```python
# MAI così
exif = image._getexif()
date_str = exif[36867]  # DateTimeOriginal grezzo

# SEMPRE così
exif = exif_sanitizer.sanitize(file_path)
date = exif['date']  # già validato e tipizzato
```

---

## Test di sicurezza richiesti

Implementa questi test in `tests/`:

### test_file_validator.py
- `test_valid_jpeg()` — file JPEG reale → True
- `test_executable_renamed_jpg()` — file EXE rinominato .jpg → False
- `test_empty_file()` — file vuoto → False
- `test_oversized_file()` — file > MAX_SIZE → False
- `test_unknown_extension()` — file .xyz → False

### test_path_guard.py
- `test_safe_join_normal()` — path normale → OK
- `test_safe_join_traversal()` — `../../etc/passwd` → ValueError
- `test_validate_highlight_name_clean()` — nome normale → nome sanitizzato
- `test_validate_highlight_name_traversal()` — `../evil` → ValueError
- `test_validate_highlight_name_empty()` — stringa vuota → ValueError

### test_exif_sanitizer.py
- `test_sanitize_valid_jpeg()` — JPEG con EXIF → dict con date
- `test_sanitize_no_exif()` — JPEG senza EXIF → dict vuoto ma non errore
- `test_sanitize_corrupt_file()` — file corrotto → dict vuoto, nessun crash

### test_audit_logger.py
- `test_log_move_creates_entry()` — log_move scrive nel file
- `test_log_is_append_only()` — istanze multiple non sovrascrivono il log
- `test_log_contains_hash()` — ogni entry contiene l'hash del file
