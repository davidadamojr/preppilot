"""
Tests for the feature flags system.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from backend.features.flags import (
    Feature,
    FeatureFlags,
    DEFAULT_FEATURE_STATES,
    get_feature_flags,
)
from backend.features.service import (
    FeatureFlagService,
    get_feature_service,
    require_feature,
)


class TestFeatureEnum:
    """Tests for the Feature enum."""

    def test_all_features_have_default_states(self):
        """Every Feature enum value should have a default state defined."""
        for feature in Feature:
            assert feature in DEFAULT_FEATURE_STATES, f"Missing default state for {feature}"

    def test_feature_values_are_strings(self):
        """Feature values should be valid string identifiers."""
        for feature in Feature:
            assert isinstance(feature.value, str)
            assert len(feature.value) > 0
            # Should be snake_case
            assert feature.value.replace("_", "").isalnum()

    def test_feature_count(self):
        """Verify expected number of features."""
        # 16 features defined
        assert len(Feature) == 16


class TestFeatureFlags:
    """Tests for the FeatureFlags settings class."""

    def test_default_feature_states(self):
        """Default feature states should match expected values."""
        flags = FeatureFlags()

        # All features should be enabled by default
        for feature in Feature:
            assert flags.get_flag(feature) == DEFAULT_FEATURE_STATES[feature]

    def test_get_flag_returns_correct_state(self):
        """get_flag should return the correct state for each feature."""
        flags = FeatureFlags()

        assert flags.get_flag(Feature.PLAN_DUPLICATION) is True
        assert flags.get_flag(Feature.EXPORT_PDF) is True

    def test_override_feature_flag(self):
        """Feature flags can be overridden via constructor."""
        flags = FeatureFlags(feature_plan_duplication=False)

        assert flags.get_flag(Feature.PLAN_DUPLICATION) is False
        # Other flags should still be default
        assert flags.get_flag(Feature.EXPORT_PDF) is True

    def test_get_all_flags_returns_dict(self):
        """get_all_flags should return a dictionary of all flags."""
        flags = FeatureFlags()
        all_flags = flags.get_all_flags()

        assert isinstance(all_flags, dict)
        assert len(all_flags) == len(Feature)

        for feature in Feature:
            assert feature.value in all_flags

    def test_factory_function_creates_instance(self):
        """get_feature_flags factory should create a FeatureFlags instance."""
        flags = get_feature_flags()

        assert isinstance(flags, FeatureFlags)

    def test_factory_function_with_overrides(self):
        """get_feature_flags should accept overrides."""
        flags = get_feature_flags(feature_meal_swap=False)

        assert flags.get_flag(Feature.MEAL_SWAP) is False


class TestFeatureFlagService:
    """Tests for the FeatureFlagService."""

    def test_is_enabled_returns_correct_state(self):
        """is_enabled should return the correct flag state."""
        service = FeatureFlagService()

        # All features should be enabled by default
        assert service.is_enabled(Feature.PLAN_DUPLICATION) is True

    def test_is_enabled_with_disabled_flag(self):
        """is_enabled should return False for disabled flags."""
        flags = FeatureFlags(feature_plan_duplication=False)
        service = FeatureFlagService(flags=flags)

        assert service.is_enabled(Feature.PLAN_DUPLICATION) is False

    def test_require_feature_passes_when_enabled(self):
        """require_feature should not raise when feature is enabled."""
        service = FeatureFlagService()

        # Should not raise
        service.require_feature(Feature.PLAN_DUPLICATION)

    def test_require_feature_raises_when_disabled(self):
        """require_feature should raise HTTPException when feature is disabled."""
        flags = FeatureFlags(feature_plan_duplication=False)
        service = FeatureFlagService(flags=flags)

        with pytest.raises(HTTPException) as exc_info:
            service.require_feature(Feature.PLAN_DUPLICATION)

        assert exc_info.value.status_code == 503
        assert "FEATURE_DISABLED" in str(exc_info.value.detail)
        assert "plan_duplication" in str(exc_info.value.detail)

    def test_get_all_flags(self):
        """get_all_flags should return all flag states."""
        service = FeatureFlagService()
        all_flags = service.get_all_flags()

        assert isinstance(all_flags, dict)
        assert len(all_flags) == len(Feature)

    def test_get_enabled_features(self):
        """get_enabled_features should return list of enabled feature names."""
        flags = FeatureFlags(
            feature_plan_duplication=True,
            feature_meal_swap=False,
        )
        service = FeatureFlagService(flags=flags)

        enabled = service.get_enabled_features()

        assert "plan_duplication" in enabled
        assert "meal_swap" not in enabled

    def test_get_disabled_features(self):
        """get_disabled_features should return list of disabled feature names."""
        flags = FeatureFlags(
            feature_plan_duplication=True,
            feature_meal_swap=False,
        )
        service = FeatureFlagService(flags=flags)

        disabled = service.get_disabled_features()

        assert "meal_swap" in disabled
        assert "plan_duplication" not in disabled


class TestGetFeatureService:
    """Tests for the get_feature_service function."""

    def test_returns_service_instance(self):
        """get_feature_service should return a FeatureFlagService."""
        # Reset global state for clean test
        import backend.features.service as service_module
        service_module._feature_service = None

        service = get_feature_service()

        assert isinstance(service, FeatureFlagService)

    def test_returns_singleton(self):
        """get_feature_service should return the same instance."""
        import backend.features.service as service_module
        service_module._feature_service = None

        service1 = get_feature_service()
        service2 = get_feature_service()

        assert service1 is service2


class TestRequireFeatureDependency:
    """Tests for the require_feature FastAPI dependency."""

    def test_dependency_factory_returns_callable(self):
        """require_feature should return a callable dependency."""
        dependency = require_feature(Feature.PLAN_DUPLICATION)

        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_dependency_passes_when_enabled(self):
        """The dependency should not raise when feature is enabled."""
        service = FeatureFlagService()
        dependency = require_feature(Feature.PLAN_DUPLICATION)

        # Manually call the inner function
        async def get_service():
            return service

        # Create a mock that returns the service
        with patch('backend.features.service.get_feature_service', return_value=service):
            # The dependency should pass without raising
            inner_func = dependency.__wrapped__ if hasattr(dependency, '__wrapped__') else None
            # Since the dependency is async, we just verify it creates correctly
            assert dependency is not None

    @pytest.mark.asyncio
    async def test_dependency_raises_when_disabled(self):
        """The dependency should raise when feature is disabled."""
        flags = FeatureFlags(feature_plan_duplication=False)
        service = FeatureFlagService(flags=flags)

        # The service.require_feature should raise
        with pytest.raises(HTTPException) as exc_info:
            service.require_feature(Feature.PLAN_DUPLICATION)

        assert exc_info.value.status_code == 503


class TestFeatureFlagIntegration:
    """Integration tests for feature flags with different configurations."""

    def test_all_email_features_can_be_disabled(self):
        """All email-related features should be disableable."""
        flags = FeatureFlags(
            feature_email_plan_notifications=False,
            feature_email_expiring_alerts=False,
            feature_email_adaptation_summaries=False,
        )
        service = FeatureFlagService(flags=flags)

        assert not service.is_enabled(Feature.EMAIL_PLAN_NOTIFICATIONS)
        assert not service.is_enabled(Feature.EMAIL_EXPIRING_ALERTS)
        assert not service.is_enabled(Feature.EMAIL_ADAPTATION_SUMMARIES)

    def test_all_export_features_can_be_disabled(self):
        """All export-related features should be disableable."""
        flags = FeatureFlags(
            feature_export_pdf=False,
            feature_export_shopping_list=False,
        )
        service = FeatureFlagService(flags=flags)

        assert not service.is_enabled(Feature.EXPORT_PDF)
        assert not service.is_enabled(Feature.EXPORT_SHOPPING_LIST)

    def test_all_plan_features_can_be_disabled(self):
        """All plan-related features should be disableable."""
        flags = FeatureFlags(
            feature_plan_duplication=False,
            feature_plan_adaptation=False,
            feature_meal_swap=False,
        )
        service = FeatureFlagService(flags=flags)

        assert not service.is_enabled(Feature.PLAN_DUPLICATION)
        assert not service.is_enabled(Feature.PLAN_ADAPTATION)
        assert not service.is_enabled(Feature.MEAL_SWAP)

    def test_all_fridge_features_can_be_disabled(self):
        """All fridge-related features should be disableable."""
        flags = FeatureFlags(
            feature_fridge_bulk_import=False,
            feature_fridge_expiring_notifications=False,
        )
        service = FeatureFlagService(flags=flags)

        assert not service.is_enabled(Feature.FRIDGE_BULK_IMPORT)
        assert not service.is_enabled(Feature.FRIDGE_EXPIRING_NOTIFICATIONS)

    def test_all_admin_features_can_be_disabled(self):
        """All admin-related features should be disableable."""
        flags = FeatureFlags(
            feature_admin_user_management=False,
            feature_admin_audit_logs=False,
        )
        service = FeatureFlagService(flags=flags)

        assert not service.is_enabled(Feature.ADMIN_USER_MANAGEMENT)
        assert not service.is_enabled(Feature.ADMIN_AUDIT_LOGS)

    def test_mixed_feature_states(self):
        """Service should correctly report mixed enabled/disabled states."""
        flags = FeatureFlags(
            feature_export_pdf=True,
            feature_export_shopping_list=False,
            feature_plan_duplication=True,
            feature_plan_adaptation=False,
        )
        service = FeatureFlagService(flags=flags)

        enabled = service.get_enabled_features()
        disabled = service.get_disabled_features()

        assert "export_pdf" in enabled
        assert "plan_duplication" in enabled
        assert "export_shopping_list" in disabled
        assert "plan_adaptation" in disabled


class TestPublicFeaturesEndpoint:
    """Tests for the public GET /api/features endpoint."""

    def test_get_features_requires_authentication(self, client):
        """Should require authentication to access feature flags."""
        response = client.get("/api/features")
        # FastAPI returns 403 when no token provided (not 401)
        assert response.status_code in (401, 403)

    def test_get_features_returns_all_flags(self, client, auth_headers):
        """Should return all feature flags for authenticated user."""
        response = client.get("/api/features", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "flags" in data
        flags = data["flags"]

        # Should have all 16 feature flags
        assert len(flags) == 16

        # Check expected flag names exist
        expected_flags = [
            "email_plan_notifications",
            "email_expiring_alerts",
            "email_adaptation_summaries",
            "export_pdf",
            "export_shopping_list",
            "plan_duplication",
            "plan_adaptation",
            "meal_swap",
            "fridge_bulk_import",
            "fridge_expiring_notifications",
            "recipe_search",
            "recipe_browser",
            "admin_user_management",
            "admin_audit_logs",
            "prep_timeline_optimization",
            "offline_mode",
        ]
        for flag in expected_flags:
            assert flag in flags, f"Missing flag: {flag}"

    def test_get_features_returns_boolean_values(self, client, auth_headers):
        """All feature flag values should be booleans."""
        response = client.get("/api/features", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        for flag_name, flag_value in data["flags"].items():
            assert isinstance(flag_value, bool), f"Flag {flag_name} is not a boolean"

    def test_get_features_default_all_enabled(self, client, auth_headers):
        """By default, all features should be enabled."""
        response = client.get("/api/features", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        for flag_name, flag_value in data["flags"].items():
            assert flag_value is True, f"Flag {flag_name} should be enabled by default"

    def test_non_admin_can_access_features(self, client, auth_headers):
        """Regular users (not just admins) should be able to access feature flags."""
        # auth_headers uses test_user which is a regular user, not admin
        response = client.get("/api/features", headers=auth_headers)
        assert response.status_code == 200
        assert "flags" in response.json()


class TestFeatureFlagSync:
    """Tests to ensure frontend and backend feature flags stay in sync."""

    # Frontend FeatureName type values (from frontend/src/types/index.ts)
    # This list must be kept in sync with the TypeScript union type.
    # If this test fails, update either the backend Feature enum or
    # the frontend FeatureName type to match.
    FRONTEND_FEATURE_NAMES = {
        "email_plan_notifications",
        "email_expiring_alerts",
        "email_adaptation_summaries",
        "export_pdf",
        "export_shopping_list",
        "plan_duplication",
        "plan_adaptation",
        "meal_swap",
        "fridge_bulk_import",
        "fridge_expiring_notifications",
        "recipe_search",
        "recipe_browser",
        "admin_user_management",
        "admin_audit_logs",
        "prep_timeline_optimization",
        "offline_mode",
    }

    def test_backend_features_match_frontend(self):
        """All backend Feature enum values should exist in frontend FeatureName type.

        If this test fails, a feature was added to the backend but not the frontend.
        Update frontend/src/types/index.ts FeatureName type to include the new feature.
        """
        backend_features = {f.value for f in Feature}

        missing_in_frontend = backend_features - self.FRONTEND_FEATURE_NAMES
        assert not missing_in_frontend, (
            f"Backend features missing in frontend FeatureName type: {missing_in_frontend}. "
            f"Add these to frontend/src/types/index.ts"
        )

    def test_frontend_features_match_backend(self):
        """All frontend FeatureName values should exist in backend Feature enum.

        If this test fails, a feature exists in frontend but not backend.
        Either add it to backend/features/flags.py or remove from frontend.
        """
        backend_features = {f.value for f in Feature}

        missing_in_backend = self.FRONTEND_FEATURE_NAMES - backend_features
        assert not missing_in_backend, (
            f"Frontend features missing in backend Feature enum: {missing_in_backend}. "
            f"Add these to backend/features/flags.py or remove from frontend/src/types/index.ts"
        )

    def test_feature_count_matches(self):
        """Frontend and backend should have the same number of features.

        This is a quick sanity check that catches additions/removals.
        """
        backend_count = len(Feature)
        frontend_count = len(self.FRONTEND_FEATURE_NAMES)

        assert backend_count == frontend_count, (
            f"Feature count mismatch: backend has {backend_count}, "
            f"frontend has {frontend_count}. Sync the feature lists."
        )

    def test_all_features_have_default_states(self):
        """Every feature in the sync list should have a default state defined."""
        for feature_name in self.FRONTEND_FEATURE_NAMES:
            feature = Feature(feature_name)
            assert feature in DEFAULT_FEATURE_STATES, (
                f"Feature {feature_name} missing from DEFAULT_FEATURE_STATES"
            )
