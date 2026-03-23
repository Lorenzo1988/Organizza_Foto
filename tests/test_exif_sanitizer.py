"""
Tests for ExifSanitizerAgent — step 15
"""
import io
import os
import tempfile
import pytest
from PIL import Image

from agents.security.exif_sanitizer import ExifSanitizerAgent


@pytest.fixture
def sanitizer():
    return ExifSanitizerAgent()


def _create_jpeg_no_exif(path: str):
    """Crea un JPEG minimal senza EXIF."""
    img = Image.new('RGB', (10, 10), color=(255, 0, 0))
    img.save(path, 'JPEG')


def _create_corrupt_file(path: str):
    """Crea un file corrotto."""
    with open(path, 'wb') as f:
        f.write(b'\xff\xd8\xff' + b'\x00' * 10)  # JPEG header tronco


class TestExifSanitizer:

    def test_sanitize_no_exif(self, tmp_path, sanitizer):
        """JPEG senza EXIF → dict vuoto ma non errore"""
        p = tmp_path / "no_exif.jpg"
        _create_jpeg_no_exif(str(p))
        result = sanitizer.sanitize(str(p))
        assert isinstance(result, dict)
        assert 'date' in result
        assert 'gps' in result
        assert result['date'] is None
        assert result['gps'] is None

    def test_sanitize_corrupt_file(self, tmp_path, sanitizer):
        """File corrotto → dict vuoto, nessun crash"""
        p = tmp_path / "corrupt.jpg"
        _create_corrupt_file(str(p))
        result = sanitizer.sanitize(str(p))
        assert isinstance(result, dict)
        assert result['date'] is None

    def test_sanitize_nonexistent(self, sanitizer):
        """File inesistente → dict con valori None, nessun crash"""
        result = sanitizer.sanitize("/nonexistent/photo.jpg")
        assert isinstance(result, dict)
        assert result['date'] is None

    def test_sanitize_returns_all_keys(self, tmp_path, sanitizer):
        """Il risultato ha sempre tutte le chiavi attese"""
        p = tmp_path / "test.jpg"
        _create_jpeg_no_exif(str(p))
        result = sanitizer.sanitize(str(p))
        assert 'date' in result
        assert 'source' in result
        assert 'gps' in result
        assert 'make' in result
        assert 'model' in result
        assert 'orientation' in result
        assert result['orientation'] == 1  # default

    def test_sanitize_uses_public_getexif(self, tmp_path, sanitizer, monkeypatch):
        """ExifSanitizerAgent non usa _getexif() (API privata)"""
        p = tmp_path / "test.jpg"
        _create_jpeg_no_exif(str(p))

        private_called = []

        original_open = Image.open

        class MockImage:
            def __init__(self, img):
                self._img = img

            def _getexif(self):
                private_called.append(True)
                return self._img._getexif()

            def getexif(self):
                return self._img.getexif()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._img.close()

        def mock_open(path):
            real = original_open(path)
            return MockImage(real)

        monkeypatch.setattr(Image, 'open', mock_open)
        sanitizer.sanitize(str(p))
        assert not private_called, "ExifSanitizerAgent ha chiamato _getexif() (privato)"

    def test_source_is_none_when_no_exif(self, tmp_path, sanitizer):
        """Senza EXIF, source deve essere 'none'"""
        p = tmp_path / "no_exif.jpg"
        _create_jpeg_no_exif(str(p))
        result = sanitizer.sanitize(str(p))
        assert result['source'] == 'none'
