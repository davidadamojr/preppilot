"""
Application configuration using Pydantic settings.

All configurable values are loaded from environment variables with sensible defaults.
This centralizes configuration management and makes the application more flexible
across different environments (development, testing, production).
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional, List

# Get the directory containing this config file (backend/)
_BACKEND_DIR = Path(__file__).parent.resolve()

# Default secret key that must be changed in production
_INSECURE_DEFAULT_SECRET = "your-secret-key-change-this-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App metadata
    app_name: str = "PrepPilot API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Logging configuration
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Timezone configuration (used for scheduling and display)
    timezone: str = "UTC"  # IANA timezone name (e.g., "America/New_York", "Europe/London")

    # Database connection
    database_url: str = "postgresql://preppilot:preppilot@localhost:5432/preppilot"

    # Database pool configuration
    database_pool_size: int = 5  # Number of persistent connections in the pool
    database_max_overflow: int = 10  # Max additional connections beyond pool_size
    database_pool_pre_ping: bool = True  # Test connections before using

    # JWT Authentication
    secret_key: str = _INSECURE_DEFAULT_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    @model_validator(mode="after")
    def validate_secret_key_in_production(self) -> "Settings":
        """Ensure secret key is changed from default in production."""
        if not self.debug and self.secret_key == _INSECURE_DEFAULT_SECRET:
            raise ValueError(
                "SECURITY ERROR: You must set a secure SECRET_KEY environment variable "
                "in production (when DEBUG=false). The default secret key is not allowed."
            )
        return self

    # CORS - development defaults, override via CORS_ORIGINS env var for production
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8000",
    ]

    # Rate limiting configuration
    rate_limit_enabled: bool = True  # Set to False to disable rate limiting globally
    rate_limit_login: str = "5/minute"  # Limit for login attempts
    rate_limit_register: str = "10/minute"  # Limit for registration
    rate_limit_password_change: str = "5/minute"  # Limit for password changes
    rate_limit_forgot_password: str = "3/minute"  # Limit for password reset requests

    # Pagination defaults
    pagination_default_page_size: int = 20  # Default items per page
    pagination_max_page_size: int = 100  # Maximum items per page
    pagination_audit_log_page_size: int = 50  # Default for audit logs
    pagination_user_audit_limit: int = 100  # Default limit for user audit logs
    pagination_user_audit_max_limit: int = 500  # Maximum limit for user audit logs
    pagination_plans_default_limit: int = 10  # Default limit for meal plans list

    # Meal plan configuration
    plan_default_days: int = 3  # Default number of days for a meal plan
    plan_max_days: int = 7  # Maximum number of days for a meal plan
    plan_max_future_days: int = 30  # How far in the future a plan can start
    max_plans_per_user: int = 50  # Maximum number of meal plans a user can have (0 = unlimited)

    # Fridge configuration
    fridge_max_freshness_days: int = 365  # Maximum freshness days for an item
    fridge_expiring_threshold_default: int = 2  # Default days threshold for "expiring soon"

    # Background jobs
    enable_background_jobs: bool = True
    freshness_decay_hour: int = 0  # Run at midnight

    # Email configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from_address: str = "noreply@preppilot.app"
    email_from_name: str = "PrepPilot"
    email_enabled: bool = False  # Disabled by default until configured

    # Email retry configuration
    email_max_retries: int = 3  # Maximum retry attempts
    email_retry_base_delay: float = 1.0  # Initial delay in seconds
    email_retry_max_delay: float = 60.0  # Maximum delay between retries
    email_retry_exponential_base: float = 2.0  # Exponential backoff multiplier

    # OpenAI configuration for LLM-powered step parsing
    openai_api_key: Optional[str] = None  # Set via OPENAI_API_KEY env var
    openai_model: str = "gpt-4o"  # Model to use for step parsing
    openai_timeout_seconds: int = 30  # Request timeout
    openai_temperature: float = 0.1  # Low temperature for consistent parsing
    openai_max_retries: int = 3  # Retry attempts for transient failures

    # Step parsing cache configuration
    step_parsing_cache_ttl_hours: int = 24  # How long to cache parsed steps

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


def get_settings(**overrides) -> Settings:
    """
    Factory function to create Settings instance.

    Useful for testing where you need to override specific values
    without modifying environment variables.

    Args:
        **overrides: Key-value pairs to override default settings

    Returns:
        Settings instance with overrides applied

    Example:
        test_settings = get_settings(debug=True, secret_key="test-key")
    """
    return Settings(**overrides)


# Global settings instance (lazy initialization for testability)
# In tests, you can reload this module or use get_settings() directly
settings = get_settings()
