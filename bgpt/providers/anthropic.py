"""
Anthropic Provider - Claude AI integration.
"""

import asyncio
import os
from typing import Any, Optional


def _resolve_model_name(config_manager: Optional[Any]) -> str:
    """Resolve Anthropic model from config first, then env, then default."""
    if config_manager is not None:
        try:
            model_from_config = config_manager.get_provider_model("anthropic")
            if model_from_config:
                return model_from_config
        except Exception:
            pass

    return os.getenv("BGPT_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")


def _resolve_api_key() -> Optional[str]:
    """Resolve Anthropic API key from env or keyring."""
    env_key = os.getenv("ANTHROPIC_API_KEY")
    if env_key:
        return env_key

    try:
        import keyring

        key = keyring.get_password("bgpt", "anthropic")
        if key:
            return key
    except Exception:
        pass

    return None

class AnthropicProvider:
    """Anthropic Claude provider."""

    def __init__(self, config_manager: Optional[Any] = None) -> None:
        self._config_manager = config_manager
        self._client = None
        self._model_name = _resolve_model_name(config_manager)
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Anthropic client."""
        try:
            import anthropic
            api_key = _resolve_api_key()
            if api_key:
                self._client = anthropic.Anthropic(api_key=api_key)
                # Remove all logging - silent initialization
        except ImportError:
            # Silently fail if anthropic not installed
            pass
        except Exception:
            # Silently fail on any other errors
            pass
    
    async def generate_response(self, prompt: str) -> Optional[str]:
        """Generate response using Anthropic."""
        if not self._client:
            return None

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=self._model_name,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            return response.content[0].text
        except Exception:
            # Remove all error logging
            return None
