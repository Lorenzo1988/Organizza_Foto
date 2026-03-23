"""
Tests for AnomalyDetectorAgent and AuditLogger monitoring — step 19
"""
import json
import os
import time
import pytest

from agents.security.anomaly_detector import AnomalyDetectorAgent
from agents.security.audit_logger import AuditLoggerAgent


class TestAnomalyDetector:

    def test_anomaly_mass_delete_triggered(self):
        """20 delete in 2 minuti → alert_callback chiamato"""
        alerts = []
        detector = AnomalyDetectorAgent(
            alert_callback=lambda t, m: alerts.append((t, m))
        )
        for i in range(20):
            detector.on_delete(f"/fake/path/photo_{i}.jpg")

        assert any(a[0] == 'MASS_DELETE' for a in alerts)

    def test_anomaly_not_triggered_below_threshold(self):
        """19 delete in 2 minuti → nessun alert"""
        alerts = []
        detector = AnomalyDetectorAgent(
            alert_callback=lambda t, m: alerts.append((t, m))
        )
        for i in range(19):
            detector.on_delete(f"/fake/path/photo_{i}.jpg")

        assert not any(a[0] == 'MASS_DELETE' for a in alerts)

    def test_anomaly_traversal_alert(self):
        """3 chiamate on_traversal_attempt() → alert_callback"""
        alerts = []
        detector = AnomalyDetectorAgent(
            alert_callback=lambda t, m: alerts.append((t, m))
        )
        for i in range(3):
            detector.on_traversal_attempt("../../etc/passwd")

        assert any(a[0] == 'PATH_TRAVERSAL' for a in alerts)

    def test_anomaly_traversal_not_triggered_below_threshold(self):
        """2 traversal → nessun alert"""
        alerts = []
        detector = AnomalyDetectorAgent(
            alert_callback=lambda t, m: alerts.append((t, m))
        )
        for i in range(2):
            detector.on_traversal_attempt("../../etc/passwd")

        assert not any(a[0] == 'PATH_TRAVERSAL' for a in alerts)

    def test_auth_failure_alert_on_second_attempt(self):
        """Dal 2° tentativo fallito → alert AUTH_FAILURE"""
        alerts = []
        detector = AnomalyDetectorAgent(
            alert_callback=lambda t, m: alerts.append((t, m))
        )
        detector.on_auth_failure(1)
        assert not any(a[0] == 'AUTH_FAILURE' for a in alerts)

        detector.on_auth_failure(2)
        assert any(a[0] == 'AUTH_FAILURE' for a in alerts)

    def test_reset_clears_counters(self):
        """reset() svuota i contatori"""
        alerts = []
        detector = AnomalyDetectorAgent(
            alert_callback=lambda t, m: alerts.append((t, m))
        )
        # Porta vicino alla soglia
        for i in range(19):
            detector.on_delete(f"/path/{i}.jpg")

        detector.reset()

        # Ora non dovrebbe triggerare con altre 19 delete
        alerts.clear()
        for i in range(19):
            detector.on_delete(f"/path2/{i}.jpg")
        assert not any(a[0] == 'MASS_DELETE' for a in alerts)


class TestAuditLoggerMonitoring:

    def test_audit_log_is_valid_json(self, tmp_path):
        """Ogni riga del log deve essere JSON valido"""
        log_path = str(tmp_path / "audit.txt")
        logger = AuditLoggerAgent(log_path)

        src = str(tmp_path / "test.jpg")
        with open(src, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 50)

        logger.log_move(src, "/dest/test.jpg")
        logger.log_delete(src)
        logger.log_skip(src, "test skip")
        logger.log_event("TEST_EVENT", "test detail")

        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parsed = json.loads(line)  # Non deve lanciare
                    assert 'ts' in parsed
                    assert 'type' in parsed

    def test_audit_log_no_absolute_paths(self, tmp_path):
        """Nessuna riga deve contenere il path assoluto della sorgente"""
        log_path = str(tmp_path / "audit.txt")
        logger = AuditLoggerAgent(log_path)

        src = str(tmp_path / "myphoto.jpg")
        with open(src, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 50)

        logger.log_move(src, str(tmp_path / "dest" / "myphoto.jpg"))
        logger.log_delete(src)

        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Il path assoluto completo non deve essere nel log
        # (solo il nome file è consentito)
        assert str(tmp_path) not in content
