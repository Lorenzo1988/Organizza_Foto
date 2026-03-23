"""
Tests for AuthenticationAgent v2 — step 17
"""
import time
import pytest

from agents.security.auth_agent import AuthenticationAgent, BCRYPT_AVAILABLE, KEYRING_AVAILABLE


@pytest.fixture
def auth(tmp_path):
    return AuthenticationAgent(app_dir=str(tmp_path))


def _make_pin(s: str) -> bytearray:
    return bytearray(s.encode('utf-8'))


@pytest.mark.skipif(not BCRYPT_AVAILABLE, reason="bcrypt non installato")
class TestAuthAgentV2:

    def test_is_first_run_true_initially(self, auth):
        """Prima del setup, is_first_run() deve essere True"""
        assert auth.is_first_run() is True

    def test_setup_pin_too_short(self, auth):
        """PIN < 4 caratteri → False"""
        ok, msg = auth.setup_pin(_make_pin("123"))
        assert ok is False
        assert "4" in msg

    def test_setup_pin_too_long(self, auth):
        """PIN > 32 caratteri → False"""
        ok, msg = auth.setup_pin(_make_pin("A" * 33))
        assert ok is False

    def test_bcrypt_used_not_sha256(self, auth, tmp_path, monkeypatch):
        """Il hash salvato deve iniziare con '$2b$' (bcrypt)"""
        monkeypatch.setattr(
            'agents.security.auth_agent.KEYRING_AVAILABLE', False
        )
        ok, _ = auth.setup_pin(_make_pin("1234"))
        assert ok is True
        fallback = tmp_path / '.auth_hash_enc'
        stored = fallback.read_text().strip()
        assert stored.startswith('$2b$'), f"Hash non bcrypt: {stored[:10]}..."

    def test_pin_memory_wiped_after_auth(self, auth, monkeypatch):
        """Dopo authenticate(), il bytearray passato deve essere tutto zeri"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        auth.setup_pin(_make_pin("mypin"))

        pin = _make_pin("mypin")
        auth.authenticate(pin)
        assert all(b == 0 for b in pin), "PIN non azzerato dopo authenticate()"

    def test_pin_memory_wiped_after_failed_auth(self, auth, monkeypatch):
        """Anche dopo auth fallita, il bytearray deve essere azzerato"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        auth.setup_pin(_make_pin("mypin"))

        wrong_pin = _make_pin("wrong")
        auth.authenticate(wrong_pin)
        assert all(b == 0 for b in wrong_pin), "PIN non azzerato dopo auth fallita"

    def test_correct_pin_authenticates(self, auth, monkeypatch):
        """PIN corretto → autenticazione riuscita"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        auth.setup_pin(_make_pin("secret1"))
        ok, msg = auth.authenticate(_make_pin("secret1"))
        assert ok is True
        assert msg == ''

    def test_wrong_pin_fails(self, auth, monkeypatch):
        """PIN errato → autenticazione fallita"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        auth.setup_pin(_make_pin("secret1"))
        ok, msg = auth.authenticate(_make_pin("wrong_pin"))
        assert ok is False

    def test_bruteforce_resistance(self, auth, monkeypatch):
        """3 tentativi falliti → lockout attivo; 4° tentativo → errore lockout"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        auth.setup_pin(_make_pin("realpin"))

        for _ in range(3):
            ok, _ = auth.authenticate(_make_pin("wrong"))
            assert ok is False

        ok, msg = auth.authenticate(_make_pin("realpin"))
        assert ok is False
        assert "bloccato" in msg.lower() or "blocc" in msg.lower()

    def test_keyring_used_when_available(self, auth, monkeypatch):
        """Mock keyring.set_password → verifica che venga chiamato"""
        called = []

        class MockKeyring:
            @staticmethod
            def set_password(service, username, password):
                called.append((service, username, password))

            @staticmethod
            def get_password(service, username):
                if called:
                    return called[-1][2]
                return None

        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', True)
        monkeypatch.setattr('agents.security.auth_agent.keyring', MockKeyring)

        ok, _ = auth.setup_pin(_make_pin("testpin"))
        assert ok is True
        assert len(called) == 1

    def test_fallback_file_when_keyring_unavailable(self, auth, tmp_path, monkeypatch):
        """Mock KEYRING_AVAILABLE = False → verifica creazione file fallback"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        ok, _ = auth.setup_pin(_make_pin("testpin"))
        assert ok is True
        fallback = tmp_path / '.auth_hash_enc'
        assert fallback.exists()

    def test_session_expires(self, auth, monkeypatch):
        """Sessione scaduta → is_session_valid() = False"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        auth.setup_pin(_make_pin("pass"))
        ok, _ = auth.authenticate(_make_pin("pass"))
        assert ok is True
        assert auth.is_session_valid() is True

        # Simula sessione scaduta
        auth._last_activity = time.time() - 3700
        assert auth.is_session_valid() is False

    def test_session_valid_after_login(self, auth, monkeypatch):
        """Dopo login riuscito, sessione deve essere valida"""
        monkeypatch.setattr('agents.security.auth_agent.KEYRING_AVAILABLE', False)
        auth.setup_pin(_make_pin("pass"))
        auth.authenticate(_make_pin("pass"))
        assert auth.is_session_valid() is True
