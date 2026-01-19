"""
External API client modules.

This module contains clients for interacting with external services
such as OpenAI for LLM-powered features.
"""

from backend.clients.openai_client import OpenAIClient

__all__ = ["OpenAIClient"]
