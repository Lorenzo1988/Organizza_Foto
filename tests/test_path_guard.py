"""
Tests for PathGuardAgent — step 14
"""
import os
import tempfile
import pytest

from agents.security.path_guard import PathGuardAgent


@pytest.fixture
def tmp_base(tmp_path):
    """Crea una directory base temporanea per i test."""
    base = tmp_path / "base"
    base.mkdir()
    return str(base)


@pytest.fixture
def guard(tmp_base):
    return PathGuardAgent(allowed_roots=[tmp_base])


class TestPathGuard:

    def test_safe_join_normal(self, guard, tmp_base):
        """Path normale → ritorna path valido"""
        result = guard.safe_join(tmp_base, "subfolder", "photo.jpg")
        assert result.endswith("photo.jpg")
        assert "subfolder" in result

    def test_safe_join_traversal(self, guard, tmp_base):
        """../../etc/passwd → ValueError"""
        with pytest.raises(ValueError):
            guard.safe_join(tmp_base, "../../etc/passwd")

    def test_safe_join_traversal_windows(self, guard, tmp_base):
        """..\\..\\Windows\\System32 → ValueError"""
        with pytest.raises(ValueError):
            guard.safe_join(tmp_base, "..", "..", "Windows")

    def test_validate_highlight_name_clean(self, guard):
        """Nome normale → nome sanitizzato (strip)"""
        result = guard.validate_highlight_name("  Viaggio_Giappone_2024  ")
        assert result == "Viaggio_Giappone_2024"

    def test_validate_highlight_name_traversal(self, guard):
        """../evil → ValueError"""
        with pytest.raises(ValueError):
            guard.validate_highlight_name("../evil")

    def test_validate_highlight_name_empty(self, guard):
        """Stringa vuota → ValueError"""
        with pytest.raises(ValueError):
            guard.validate_highlight_name("")

    def test_validate_highlight_name_spaces_only(self, guard):
        """Solo spazi → ValueError"""
        with pytest.raises(ValueError):
            guard.validate_highlight_name("   ")

    def test_validate_highlight_name_too_long(self, guard):
        """Nome > 100 caratteri → ValueError"""
        with pytest.raises(ValueError):
            guard.validate_highlight_name("A" * 101)

    def test_validate_highlight_name_accented(self, guard):
        """Lettere accentate → OK"""
        result = guard.validate_highlight_name("Vacanze_Natàlè")
        assert result == "Vacanze_Natàlè"

    def test_is_safe_path_inside(self, guard, tmp_base):
        """Path dentro la sandbox → True"""
        inside = os.path.join(tmp_base, "subfolder", "photo.jpg")
        assert guard.is_safe_path(inside) is True

    def test_is_safe_path_outside(self, guard):
        """Path fuori dalla sandbox → False"""
        assert guard.is_safe_path("/etc/passwd") is False

    def test_add_allowed_root(self, tmp_path):
        """add_allowed_root aggiunge una nuova radice"""
        extra = tmp_path / "extra"
        extra.mkdir()
        guard = PathGuardAgent(allowed_roots=[])
        guard.add_allowed_root(str(extra))
        result = guard.safe_join(str(extra), "file.jpg")
        assert "file.jpg" in result

    def test_validate_backslash_in_name(self, guard):
        """Nome con backslash → ValueError"""
        with pytest.raises(ValueError):
            guard.validate_highlight_name("evil\\path")

    def test_validate_slash_in_name(self, guard):
        """Nome con slash → ValueError"""
        with pytest.raises(ValueError):
            guard.validate_highlight_name("evil/path")
