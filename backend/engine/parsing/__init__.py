"""
Step parsing module for prep timeline optimization.

This module provides parsers for extracting structured data from recipe steps
to enable intelligent batching and parallel scheduling.

Two parsing strategies are available:
1. HeuristicStepParser - Fast, rule-based parsing using keyword matching
2. LLMStepParser - LLM-powered parsing with semantic normalization (when enabled)

The StepParserFactory selects the appropriate parser based on feature flags.
"""

from backend.engine.parsing.models import ParsedPrepStep, Equipment, Phase
from backend.engine.parsing.protocol import StepParser
from backend.engine.parsing.factory import create_step_parser
from backend.engine.parsing.heuristic import HeuristicStepParser
from backend.engine.parsing.llm import LLMStepParser
from backend.engine.parsing.cache import StepParsingCache, get_step_cache

__all__ = [
    # Core models
    "ParsedPrepStep",
    "Equipment",
    "Phase",
    # Protocol
    "StepParser",
    # Parsers
    "HeuristicStepParser",
    "LLMStepParser",
    # Factory
    "create_step_parser",
    # Cache
    "StepParsingCache",
    "get_step_cache",
]
