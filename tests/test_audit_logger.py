"""
Tests for AuditLoggerAgent v2 — step 16
"""
import json
import os
import tempfile
import pytest

from agents.security.audit_logger import AuditLoggerAgent


@pytest.fixture
def log_file(tmp_path):
    return str(tmp_path / "audit_log.txt")


@pytest.fixture
def logger_instance(log_file):
    return AuditLoggerAgent(log_file)


def _read_log_entries(log_path: str) -> list:
    entries = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


class TestAuditLogger:

    def test_log_move_creates_entry(self, logger_instance, log_file, tmp_path):
        """log_move scrive nel file"""
        src = str(tmp_path / "photo.jpg")
        dst = str(tmp_path / "dest" / "photo.jpg")
        # Crea file sorgente per il hash
        with open(src, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 100)

        logger_instance.log_move(src, dst)

        entries = _read_log_entries(log_file)
        move_entries = [e for e in entries if e['type'] == 'MOVE']
        assert len(move_entries) == 1
        assert move_entries[0]['file'] == 'photo.jpg'

    def test_log_is_append_only(self, log_file, tmp_path):
        """Istanze multiple non sovrascrivono il log"""
        src = str(tmp_path / "a.jpg")
        with open(src, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 10)

        logger1 = AuditLoggerAgent(log_file)
        logger1.log_move(src, str(tmp_path / "dst1" / "a.jpg"))

        logger2 = AuditLoggerAgent(log_file)
        logger2.log_move(src, str(tmp_path / "dst2" / "a.jpg"))

        entries = _read_log_entries(log_file)
        move_entries = [e for e in entries if e['type'] == 'MOVE']
        assert len(move_entries) == 2

    def test_log_contains_hash(self, logger_instance, log_file, tmp_path):
        """Ogni entry di MOVE contiene l'hash del file"""
        src = str(tmp_path / "photo.jpg")
        with open(src, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 100)

        logger_instance.log_move(src, str(tmp_path / "dst" / "photo.jpg"))

        entries = _read_log_entries(log_file)
        move_entries = [e for e in entries if e['type'] == 'MOVE']
        assert len(move_entries) == 1
        assert 'src_hash' in move_entries[0]
        assert len(move_entries[0]['src_hash']) > 0

    def test_log_is_valid_json(self, logger_instance, log_file, tmp_path):
        """Ogni riga del log deve essere JSON valido"""
        src = str(tmp_path / "test.jpg")
        with open(src, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 50)

        logger_instance.log_move(src, "/some/dest/test.jpg")
        logger_instance.log_skip(src, "file corrotto")
        logger_instance.log_delete(src)
        logger_instance.log_event("CUSTOM_EVENT", "dettaglio test")

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parsed = json.loads(line)
                    assert 'ts' in parsed
                    assert 'type' in parsed

    def test_log_no_absolute_paths(self, logger_instance, log_file, tmp_path):
        """Nessuna riga deve contenere il path assoluto completo della sorgente"""
        src = str(tmp_path / "myphoto.jpg")
        with open(src, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 50)
        dst = str(tmp_path / "dest" / "myphoto.jpg")

        logger_instance.log_move(src, dst)

        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Il path assoluto completo non deve comparire nel log
        # (solo il nome del file e l'hash)
        assert str(tmp_path) not in content

    def test_log_skip_with_list_reason(self, logger_instance, log_file, tmp_path):
        """log_skip accetta sia str che list"""
        src = str(tmp_path / "bad.jpg")
        with open(src, 'wb') as f:
            f.write(b'\x00' * 10)

        logger_instance.log_skip(src, ["errore 1", "errore 2"])

        entries = _read_log_entries(log_file)
        skip_entries = [e for e in entries if e['type'] == 'SKIP']
        assert len(skip_entries) == 1
        assert "errore 1" in skip_entries[0]['detail']

    def test_session_start_on_init(self, log_file):
        """All'init viene scritta una entry SESSION_START"""
        _ = AuditLoggerAgent(log_file)
        entries = _read_log_entries(log_file)
        starts = [e for e in entries if e['type'] == 'SESSION_START']
        assert len(starts) >= 1
