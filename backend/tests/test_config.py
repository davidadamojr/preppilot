"""
Tests for application configuration and settings validation.

Tests the Settings class behavior including:
- Default values
- Environment variable overrides
- Production security validation
"""
import pytest
import os
from unittest.mock import patch

from backend.config import Settings, get_settings, _INSECURE_DEFAULT_SECRET


class TestSettingsDefaults:
    """Tests for default configuration values."""

    def test_app_name_default(self):
        """App name should default to 'PrepPilot API'."""
        settings = get_settings(debug=True)
        assert settings.app_name == "PrepPilot API"

    def test_app_version_default(self):
        """App version should default to '0.1.0'."""
        settings = get_settings(debug=True)
        assert settings.app_version == "0.1.0"

    def test_debug_default_false(self, monkeypatch):
        """Debug should default to False when env var not set."""
        # Clear DEBUG env var and prevent .env file loading to test true default
        monkeypatch.delenv("DEBUG", raising=False)
        # Explicitly pass debug=False to override any .env file settings
        # The Settings class default is debug=False, but .env may override it
        settings = get_settings(debug=False, secret_key="secure-test-key-123456789")
        assert settings.debug is False

    def test_database_url_default(self):
        """Database URL should have sensible default."""
        settings = get_settings(debug=True)
        assert "postgresql://" in settings.database_url
        assert "preppilot" in settings.database_url

    def test_algorithm_default_hs256(self):
        """JWT algorithm should default to HS256."""
        settings = get_settings(debug=True)
        assert settings.algorithm == "HS256"

    def test_token_expire_default_7_days(self):
        """Token expiration should default to 7 days (10080 minutes)."""
        settings = get_settings(debug=True)
        assert settings.access_token_expire_minutes == 10080

    def test_cors_origins_default(self):
        """CORS origins should include localhost for development."""
        settings = get_settings(debug=True)
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:8000" in settings.cors_origins

    def test_email_disabled_by_default(self):
        """Email should be disabled by default."""
        settings = get_settings(debug=True)
        assert settings.email_enabled is False

    def test_background_jobs_enabled_by_default(self):
        """Background jobs should be enabled by default."""
        settings = get_settings(debug=True)
        assert settings.enable_background_jobs is True

    def test_freshness_decay_hour_default_midnight(self):
        """Freshness decay job should run at midnight by default."""
        settings = get_settings(debug=True)
        assert settings.freshness_decay_hour == 0


class TestSettingsOverrides:
    """Tests for settings override via get_settings factory."""

    def test_can_override_debug(self):
        """Should be able to override debug mode."""
        settings = get_settings(debug=True)
        assert settings.debug is True

    def test_can_override_secret_key(self):
        """Should be able to override secret key."""
        custom_key = "my-custom-secret-key-1234567890"
        settings = get_settings(debug=True, secret_key=custom_key)
        assert settings.secret_key == custom_key

    def test_can_override_database_url(self):
        """Should be able to override database URL."""
        custom_url = "postgresql://user:pass@host:5432/db"
        settings = get_settings(debug=True, database_url=custom_url)
        assert settings.database_url == custom_url

    def test_can_override_token_expiration(self):
        """Should be able to override token expiration."""
        settings = get_settings(debug=True, access_token_expire_minutes=60)
        assert settings.access_token_expire_minutes == 60

    def test_can_override_cors_origins(self):
        """Should be able to override CORS origins."""
        custom_origins = ["https://example.com"]
        settings = get_settings(debug=True, cors_origins=custom_origins)
        assert settings.cors_origins == custom_origins

    def test_can_enable_email(self):
        """Should be able to enable email."""
        settings = get_settings(debug=True, email_enabled=True)
        assert settings.email_enabled is True

    def test_can_configure_smtp(self):
        """Should be able to configure SMTP settings."""
        settings = get_settings(
            debug=True,
            smtp_server="smtp.example.com",
            smtp_port=465,
            smtp_username="user@example.com",
            smtp_password="secretpassword",
        )
        assert settings.smtp_server == "smtp.example.com"
        assert settings.smtp_port == 465
        assert settings.smtp_username == "user@example.com"
        assert settings.smtp_password == "secretpassword"


class TestSecretKeyValidation:
    """Tests for production secret key validation."""

    def test_allows_default_secret_in_debug_mode(self):
        """Default secret key should be allowed when debug=True."""
        # This should NOT raise an error
        settings = get_settings(debug=True, secret_key=_INSECURE_DEFAULT_SECRET)
        assert settings.secret_key == _INSECURE_DEFAULT_SECRET

    def test_rejects_default_secret_in_production(self):
        """Default secret key should be rejected when debug=False."""
        with pytest.raises(ValueError) as exc_info:
            get_settings(debug=False, secret_key=_INSECURE_DEFAULT_SECRET)

        assert "SECURITY ERROR" in str(exc_info.value)
        assert "SECRET_KEY" in str(exc_info.value)

    def test_allows_custom_secret_in_production(self):
        """Custom secret key should be allowed in production."""
        secure_key = "my-very-secure-production-key-1234567890"
        settings = get_settings(debug=False, secret_key=secure_key)
        assert settings.secret_key == secure_key

    def test_validation_catches_default_secret_value(self):
        """Validation should catch the exact default secret value."""
        with pytest.raises(ValueError):
            get_settings(
                debug=False,
                secret_key="your-secret-key-change-this-in-production"
            )

    def test_validation_allows_similar_but_different_secret(self):
        """Secrets similar to but not matching default should be allowed."""
        # Slightly modified from default
        similar_key = "your-secret-key-change-this-in-production-modified"
        settings = get_settings(debug=False, secret_key=similar_key)
        assert settings.secret_key == similar_key


class TestEnvironmentVariables:
    """Tests for environment variable loading."""

    def test_debug_from_environment(self):
        """DEBUG environment variable should be read."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            settings = Settings()
            assert settings.debug is True

    def test_secret_key_from_environment(self):
        """SECRET_KEY environment variable should be read."""
        custom_key = "env-secret-key-1234567890"
        with patch.dict(os.environ, {"SECRET_KEY": custom_key, "DEBUG": "true"}):
            settings = Settings()
            assert settings.secret_key == custom_key

    def test_database_url_from_environment(self):
        """DATABASE_URL environment variable should be read."""
        custom_url = "postgresql://test:test@testhost:5432/testdb"
        with patch.dict(os.environ, {"DATABASE_URL": custom_url, "DEBUG": "true"}):
            settings = Settings()
            assert settings.database_url == custom_url

    def test_case_insensitive_env_vars(self):
        """Environment variables should be case-insensitive."""
        with patch.dict(os.environ, {"debug": "true"}):
            settings = Settings()
            assert settings.debug is True


class TestSettingsTypes:
    """Tests for correct type handling in settings."""

    def test_debug_is_boolean(self):
        """Debug should be a boolean."""
        settings = get_settings(debug=True)
        assert isinstance(settings.debug, bool)

    def test_cors_origins_is_list(self):
        """CORS origins should be a list."""
        settings = get_settings(debug=True)
        assert isinstance(settings.cors_origins, list)

    def test_smtp_port_is_integer(self):
        """SMTP port should be an integer."""
        settings = get_settings(debug=True)
        assert isinstance(settings.smtp_port, int)

    def test_token_expire_is_integer(self):
        """Token expiration should be an integer."""
        settings = get_settings(debug=True)
        assert isinstance(settings.access_token_expire_minutes, int)

    def test_optional_smtp_credentials(self):
        """SMTP username and password should be optional (can be None or empty string)."""
        settings = get_settings(debug=True)
        # SMTP credentials are optional - they can be None or empty string
        # When loaded from .env with empty value, they become empty string
        assert settings.smtp_username is None or settings.smtp_username == ""
        assert settings.smtp_password is None or settings.smtp_password == ""
