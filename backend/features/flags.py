"""
Feature flag definitions and configuration.

This module defines all available feature flags and their default states.
Feature flags can be overridden via environment variables.
"""

from enum import Enum
from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Feature(str, Enum):
    """
    Enumeration of all feature flags in the application.

    Each feature flag represents a toggleable capability that can be
    enabled or disabled without code changes.

    Naming convention: FEATURE_<CATEGORY>_<NAME>
    """

    # Email features
    EMAIL_PLAN_NOTIFICATIONS = "email_plan_notifications"
    EMAIL_EXPIRING_ALERTS = "email_expiring_alerts"
    EMAIL_ADAPTATION_SUMMARIES = "email_adaptation_summaries"

    # Export features
    EXPORT_PDF = "export_pdf"
    EXPORT_SHOPPING_LIST = "export_shopping_list"

    # Plan features
    PLAN_DUPLICATION = "plan_duplication"
    PLAN_ADAPTATION = "plan_adaptation"
    MEAL_SWAP = "meal_swap"

    # Fridge features
    FRIDGE_BULK_IMPORT = "fridge_bulk_import"
    FRIDGE_EXPIRING_NOTIFICATIONS = "fridge_expiring_notifications"

    # Recipe features
    RECIPE_SEARCH = "recipe_search"
    RECIPE_BROWSER = "recipe_browser"

    # Admin features
    ADMIN_USER_MANAGEMENT = "admin_user_management"
    ADMIN_AUDIT_LOGS = "admin_audit_logs"

    # Experimental features
    PREP_TIMELINE_OPTIMIZATION = "prep_timeline_optimization"
    LLM_STEP_PARSING = "llm_step_parsing"
    OFFLINE_MODE = "offline_mode"


# Default states for all features (True = enabled by default)
DEFAULT_FEATURE_STATES: Dict[Feature, bool] = {
    # Email features - default enabled (if email is configured)
    Feature.EMAIL_PLAN_NOTIFICATIONS: True,
    Feature.EMAIL_EXPIRING_ALERTS: True,
    Feature.EMAIL_ADAPTATION_SUMMARIES: True,
    # Export features - default enabled
    Feature.EXPORT_PDF: True,
    Feature.EXPORT_SHOPPING_LIST: True,
    # Plan features - default enabled
    Feature.PLAN_DUPLICATION: True,
    Feature.PLAN_ADAPTATION: True,
    Feature.MEAL_SWAP: True,
    # Fridge features - default enabled
    Feature.FRIDGE_BULK_IMPORT: True,
    Feature.FRIDGE_EXPIRING_NOTIFICATIONS: True,
    # Recipe features - default enabled
    Feature.RECIPE_SEARCH: True,
    Feature.RECIPE_BROWSER: True,
    # Admin features - default enabled
    Feature.ADMIN_USER_MANAGEMENT: True,
    Feature.ADMIN_AUDIT_LOGS: True,
    # Experimental features
    Feature.PREP_TIMELINE_OPTIMIZATION: True,
    Feature.LLM_STEP_PARSING: True,  # Enabled by default when OpenAI API key is configured
    Feature.OFFLINE_MODE: True,
}


class FeatureFlags(BaseSettings):
    """
    Feature flag settings loaded from environment variables.

    Each feature flag can be toggled via an environment variable:
    FEATURE_<FLAG_NAME>=true/false

    Example:
        FEATURE_EMAIL_PLAN_NOTIFICATIONS=false
        FEATURE_PLAN_DUPLICATION=false
    """

    # Email features
    feature_email_plan_notifications: bool = DEFAULT_FEATURE_STATES[
        Feature.EMAIL_PLAN_NOTIFICATIONS
    ]
    feature_email_expiring_alerts: bool = DEFAULT_FEATURE_STATES[
        Feature.EMAIL_EXPIRING_ALERTS
    ]
    feature_email_adaptation_summaries: bool = DEFAULT_FEATURE_STATES[
        Feature.EMAIL_ADAPTATION_SUMMARIES
    ]

    # Export features
    feature_export_pdf: bool = DEFAULT_FEATURE_STATES[Feature.EXPORT_PDF]
    feature_export_shopping_list: bool = DEFAULT_FEATURE_STATES[
        Feature.EXPORT_SHOPPING_LIST
    ]

    # Plan features
    feature_plan_duplication: bool = DEFAULT_FEATURE_STATES[Feature.PLAN_DUPLICATION]
    feature_plan_adaptation: bool = DEFAULT_FEATURE_STATES[Feature.PLAN_ADAPTATION]
    feature_meal_swap: bool = DEFAULT_FEATURE_STATES[Feature.MEAL_SWAP]

    # Fridge features
    feature_fridge_bulk_import: bool = DEFAULT_FEATURE_STATES[Feature.FRIDGE_BULK_IMPORT]
    feature_fridge_expiring_notifications: bool = DEFAULT_FEATURE_STATES[
        Feature.FRIDGE_EXPIRING_NOTIFICATIONS
    ]

    # Recipe features
    feature_recipe_search: bool = DEFAULT_FEATURE_STATES[Feature.RECIPE_SEARCH]
    feature_recipe_browser: bool = DEFAULT_FEATURE_STATES[Feature.RECIPE_BROWSER]

    # Admin features
    feature_admin_user_management: bool = DEFAULT_FEATURE_STATES[
        Feature.ADMIN_USER_MANAGEMENT
    ]
    feature_admin_audit_logs: bool = DEFAULT_FEATURE_STATES[Feature.ADMIN_AUDIT_LOGS]

    # Experimental features
    feature_prep_timeline_optimization: bool = DEFAULT_FEATURE_STATES[
        Feature.PREP_TIMELINE_OPTIMIZATION
    ]
    feature_llm_step_parsing: bool = DEFAULT_FEATURE_STATES[Feature.LLM_STEP_PARSING]
    feature_offline_mode: bool = DEFAULT_FEATURE_STATES[Feature.OFFLINE_MODE]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore non-feature-flag environment variables
    )

    def get_flag(self, feature: Feature) -> bool:
        """
        Get the current state of a feature flag.

        Args:
            feature: The feature to check

        Returns:
            True if the feature is enabled, False otherwise
        """
        attr_name = f"feature_{feature.value}"
        return getattr(self, attr_name, DEFAULT_FEATURE_STATES.get(feature, False))

    def get_all_flags(self) -> Dict[str, bool]:
        """
        Get the current state of all feature flags.

        Returns:
            Dictionary mapping feature names to their enabled states
        """
        return {feature.value: self.get_flag(feature) for feature in Feature}


def get_feature_flags(**overrides) -> FeatureFlags:
    """
    Factory function to create FeatureFlags instance.

    Useful for testing where you need to override specific flags
    without modifying environment variables.

    Args:
        **overrides: Key-value pairs to override default flags

    Returns:
        FeatureFlags instance with overrides applied
    """
    return FeatureFlags(**overrides)


# Global feature flags instance
feature_flags = get_feature_flags()
