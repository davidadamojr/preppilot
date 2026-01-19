"""
OpenAI API client with retry logic and error handling.

Provides a wrapper around the OpenAI API for LLM-powered step parsing.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class OpenAIClientError(Exception):
    """Base exception for OpenAI client errors."""

    pass


class OpenAIClient:
    """
    Client for interacting with OpenAI API.

    Provides methods for:
    - Structured JSON responses for step parsing
    - Automatic retry with exponential backoff
    - Response caching (via LLMStepParser)

    Example:
        >>> client = OpenAIClient()
        >>> response = client.parse_steps(
        ...     system_prompt="You are a culinary assistant...",
        ...     user_prompt="Parse these steps: 1. Dice onion...",
        ...     response_format={"type": "json_object"}
        ... )
    """

    def __init__(self):
        """Initialize the OpenAI client."""
        self._client: Optional[Any] = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazily initialize the OpenAI client."""
        if self._initialized:
            return

        if not settings.openai_api_key:
            raise OpenAIClientError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY environment variable."
            )

        try:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_timeout_seconds,
                max_retries=settings.openai_max_retries,
            )
            self._initialized = True
        except ImportError:
            raise OpenAIClientError(
                "openai package not installed. Run: pip install openai>=1.10.0"
            )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Send a completion request to OpenAI.

        Args:
            system_prompt: Instructions for the model behavior.
            user_prompt: The user's input to process.
            response_format: Optional format specification (e.g., {"type": "json_object"}).

        Returns:
            The model's response content as a string.

        Raises:
            OpenAIClientError: If the API call fails.
        """
        self._ensure_initialized()

        try:
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            kwargs: Dict[str, Any] = {
                "model": settings.openai_model,
                "messages": messages,
                "temperature": settings.openai_temperature,
            }

            if response_format:
                kwargs["response_format"] = response_format

            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise OpenAIClientError(f"OpenAI API call failed: {e}") from e

    def parse_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Send a completion request and parse the JSON response.

        This is a convenience method that combines complete() with JSON parsing.

        Args:
            system_prompt: Instructions for the model behavior.
            user_prompt: The user's input to process.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            OpenAIClientError: If the API call fails or JSON parsing fails.
        """
        import json

        response = self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise OpenAIClientError(f"Failed to parse JSON response: {e}") from e
