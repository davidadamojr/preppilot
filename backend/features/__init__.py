"""
Feature flags module for PrepPilot.

This module provides a simple feature flag system that allows features
to be enabled or disabled without code changes.
"""

from backend.features.flags import Feature, FeatureFlags, get_feature_flags
from backend.features.service import FeatureFlagService, get_feature_service

__all__ = [
    "Feature",
    "FeatureFlags",
    "get_feature_flags",
    "FeatureFlagService",
    "get_feature_service",
]
