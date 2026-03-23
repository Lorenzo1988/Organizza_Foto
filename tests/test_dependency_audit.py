"""
Tests for DependencyAuditAgent — step 20
"""
import time
import pytest

from agents.security.dependency_audit import DependencyAuditAgent


@pytest.fixture
def audit_agent(tmp_path):
    return DependencyAuditAgent(app_dir=str(tmp_path))


class TestDependencyAudit:

    def test_audit_runs_when_cache_missing(self, audit_agent):
        """Senza .last_audit → should_run() = True"""
        assert audit_agent.should_run() is True

    def test_audit_skipped_within_7_days(self, audit_agent):
        """Cache recente → should_run() = False"""
        # Scrivi timestamp recente
        audit_agent.cache_path.write_text(str(time.time()))
        assert audit_agent.should_run() is False

    def test_audit_runs_after_7_days(self, audit_agent):
        """Cache di 8 giorni fa → should_run() = True"""
        old_time = time.time() - (8 * 86400)
        audit_agent.cache_path.write_text(str(old_time))
        assert audit_agent.should_run() is True

    def test_audit_graceful_if_pip_audit_missing(self, audit_agent, monkeypatch):
        """pip-audit non installato → run() ritorna []"""
        import subprocess

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("pip-audit not found")

        monkeypatch.setattr(subprocess, 'run', mock_run)
        result = audit_agent.run()
        assert result == []

    def test_audit_graceful_on_timeout(self, audit_agent, monkeypatch):
        """Timeout di pip-audit → run() ritorna []"""
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired("pip-audit", 60)

        monkeypatch.setattr(subprocess, 'run', mock_run)
        result = audit_agent.run()
        assert result == []

    def test_audit_returns_empty_on_no_vulns(self, audit_agent, monkeypatch):
        """pip-audit returncode 0 → ritorna []"""
        import subprocess

        mock_result = type('Result', (), {
            'returncode': 0,
            'stdout': '{"dependencies": []}',
            'stderr': ''
        })()

        monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: mock_result)
        result = audit_agent.run()
        assert result == []

    def test_format_warning_empty(self, audit_agent):
        """Nessuna vulnerabilità → stringa vuota"""
        assert audit_agent.format_warning([]) == ''

    def test_format_warning_with_vulns(self, audit_agent):
        """Vulnerabilità trovate → stringa con informazioni"""
        vulns = [{
            'package': 'Pillow',
            'version': '10.0.0',
            'cve': 'CVE-2024-1234',
            'description': 'Test vulnerability',
            'fix_versions': ['10.4.0'],
        }]
        warning = audit_agent.format_warning(vulns)
        assert 'Pillow' in warning
        assert 'CVE-2024-1234' in warning
        assert '10.4.0' in warning

    def test_cache_written_after_run(self, audit_agent, monkeypatch):
        """Dopo run(), .last_audit viene aggiornato"""
        import subprocess
        import json

        mock_result = type('Result', (), {
            'returncode': 0,
            'stdout': json.dumps({'dependencies': []}),
            'stderr': ''
        })()
        monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: mock_result)

        audit_agent.run()
        assert audit_agent.cache_path.exists()
