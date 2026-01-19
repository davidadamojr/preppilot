"""
Factory for creating step parsers based on configuration.

Selects between LLM-based parsing and heuristic parsing based on
feature flags and API key availability.
"""

from backend.engine.parsing.protocol import StepParser


def create_step_parser() -> StepParser:
    """
    Create the appropriate step parser based on configuration.

    Returns LLMStepParser if:
    1. LLM_STEP_PARSING feature flag is enabled
    2. OpenAI API key is configured

    Otherwise returns HeuristicStepParser as fallback.

    Returns:
        StepParser implementation (LLMStepParser or HeuristicStepParser)
    """
    from backend.config import settings
    from backend.features.flags import Feature, feature_flags

    # Check if LLM parsing is enabled
    llm_enabled = feature_flags.get_flag(Feature.LLM_STEP_PARSING)

    if llm_enabled and settings.openai_api_key:
        from backend.engine.parsing.llm import LLMStepParser

        return LLMStepParser()

    # Fallback to heuristic parser
    from backend.engine.parsing.heuristic import HeuristicStepParser

    return HeuristicStepParser()
