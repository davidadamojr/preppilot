"""
Feature flag service for checking and managing feature states.

This service provides a clean interface for checking feature flag states
and can be injected into route handlers as a dependency.
"""

from typing import Dict, Optional
from fastapi import Depends, HTTPException, status

from backend.features.flags import Feature, FeatureFlags, feature_flags


class FeatureFlagService:
    """
    Service for evaluating feature flags.

    This service provides methods to check if features are enabled
    and to retrieve information about all feature flags.

    Attributes:
        flags: The FeatureFlags configuration instance
    """

    def __init__(self, flags: Optional[FeatureFlags] = None):
        """
        Initialize the feature flag service.

        Args:
            flags: Optional FeatureFlags instance. Uses global instance if not provided.
        """
        self.flags = flags or feature_flags

    def is_enabled(self, feature: Feature) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature: The feature to check

        Returns:
            True if the feature is enabled, False otherwise

        Example:
            if feature_service.is_enabled(Feature.PLAN_DUPLICATION):
                # Allow plan duplication
                pass
        """
        return self.flags.get_flag(feature)

    def require_feature(self, feature: Feature) -> None:
        """
        Require a feature to be enabled, raising an exception if not.

        Args:
            feature: The feature to require

        Raises:
            HTTPException: 503 Service Unavailable if feature is disabled
        """
        if not self.is_enabled(feature):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "FEATURE_DISABLED",
                    "message": f"Feature '{feature.value}' is currently disabled",
                    "feature": feature.value,
                },
            )

    def get_all_flags(self) -> Dict[str, bool]:
        """
        Get the current state of all feature flags.

        Returns:
            Dictionary mapping feature names to their enabled states
        """
        return self.flags.get_all_flags()

    def get_enabled_features(self) -> list[str]:
        """
        Get a list of all enabled feature names.

        Returns:
            List of enabled feature names
        """
        return [name for name, enabled in self.get_all_flags().items() if enabled]

    def get_disabled_features(self) -> list[str]:
        """
        Get a list of all disabled feature names.

        Returns:
            List of disabled feature names
        """
        return [name for name, enabled in self.get_all_flags().items() if not enabled]


# Global service instance
_feature_service: Optional[FeatureFlagService] = None


def get_feature_service() -> FeatureFlagService:
    """
    Get or create the global feature flag service instance.

    This is used as a FastAPI dependency for injecting the service
    into route handlers.

    Returns:
        The global FeatureFlagService instance
    """
    global _feature_service
    if _feature_service is None:
        _feature_service = FeatureFlagService()
    return _feature_service


def require_feature(feature: Feature):
    """
    FastAPI dependency factory that requires a feature to be enabled.

    Usage:
        @app.post("/plans/{plan_id}/duplicate")
        def duplicate_plan(
            plan_id: UUID,
            _: None = Depends(require_feature(Feature.PLAN_DUPLICATION)),
        ):
            # This endpoint only works if PLAN_DUPLICATION is enabled
            pass

    Args:
        feature: The feature that must be enabled

    Returns:
        A dependency function that raises HTTPException if feature is disabled
    """

    def check_feature(
        feature_service: FeatureFlagService = Depends(get_feature_service),
    ) -> None:
        feature_service.require_feature(feature)

    return check_feature
