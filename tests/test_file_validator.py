"""
Tests for FileValidatorAgent — step 13
"""
import os
import struct
import tempfile
import pytest

from agents.security.file_validator import FileValidatorAgent


@pytest.fixture
def validator():
    return FileValidatorAgent(max_size_mb=200)


def _write_file(path: str, content: bytes):
    with open(path, 'wb') as f:
        f.write(content)


# Magic bytes JPEG
JPEG_MAGIC = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00'
# Magic bytes EXE (MZ header)
EXE_MAGIC = b'MZ' + b'\x00' * 50


class TestFileValidator:

    def test_valid_jpeg(self, tmp_path):
        """File JPEG valido → True"""
        p = tmp_path / "photo.jpg"
        _write_file(str(p), JPEG_MAGIC + b'\x00' * 100)
        assert FileValidatorAgent().validate(str(p)) is True

    def test_executable_renamed_jpg(self, tmp_path):
        """File EXE rinominato .jpg → False (magic bytes non validi)"""
        p = tmp_path / "evil.jpg"
        _write_file(str(p), EXE_MAGIC)
        result = FileValidatorAgent().validate(str(p))
        assert result is False
        errors = FileValidatorAgent()
        errors.validate(str(p))
        assert any("magic" in e.lower() or "non validi" in e.lower()
                   for e in errors.get_errors())

    def test_empty_file(self, tmp_path):
        """File vuoto → False"""
        p = tmp_path / "empty.jpg"
        _write_file(str(p), b'')
        v = FileValidatorAgent()
        assert v.validate(str(p)) is False
        assert any("vuoto" in e.lower() for e in v.get_errors())

    def test_oversized_file(self, tmp_path):
        """File > MAX_SIZE → False"""
        p = tmp_path / "huge.jpg"
        # Crea file di 1 MB, limite a 0 MB → sempre troppo grande
        v = FileValidatorAgent(max_size_mb=0)
        _write_file(str(p), JPEG_MAGIC + b'\x00' * 1000)
        assert v.validate(str(p)) is False

    def test_unknown_extension(self, tmp_path):
        """File .xyz → False (estensione non supportata)"""
        p = tmp_path / "photo.xyz"
        _write_file(str(p), JPEG_MAGIC + b'\x00' * 100)
        v = FileValidatorAgent()
        assert v.validate(str(p)) is False
        assert any("estensione" in e.lower() for e in v.get_errors())

    def test_nonexistent_file(self):
        """File inesistente → False"""
        v = FileValidatorAgent()
        assert v.validate("/nonexistent/path/photo.jpg") is False

    def test_get_errors_empty_on_valid(self, tmp_path):
        """Nessun errore su file valido"""
        p = tmp_path / "ok.jpg"
        _write_file(str(p), JPEG_MAGIC + b'\x00' * 100)
        v = FileValidatorAgent()
        v.validate(str(p))
        assert v.get_errors() == []

    def test_png_magic(self, tmp_path):
        """File PNG valido → True"""
        p = tmp_path / "photo.png"
        png_magic = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        _write_file(str(p), png_magic)
        assert FileValidatorAgent().validate(str(p)) is True
