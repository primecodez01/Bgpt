"""
Gemini Provider - Google Gemini AI integration.
"""

import asyncio
import os
import warnings
from typing import Any, Optional


def _resolve_model_name(config_manager: Optional[Any]) -> str:
    """Resolve Gemini model from config first, then env, then default."""
    if config_manager is not None:
        try:
            model_from_config = config_manager.get_provider_model("gemini")
            if model_from_config:
                return model_from_config
        except Exception:
            pass

    return os.getenv("BGPT_GEMINI_MODEL", "gemini-2.5-flash")


def _resolve_api_key() -> Optional[str]:
    """Resolve Gemini API key from env or keyring."""
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key

    try:
        import keyring

        key = keyring.get_password("bgpt", "gemini")
        if key:
            return key
    except Exception:
        pass

    return None

class GeminiProvider:
    """Google Gemini AI provider."""

    def __init__(self, config_manager: Optional[Any] = None) -> None:
        self._config_manager = config_manager
        self._client: Optional[Any] = None
        self._legacy_model: Optional[Any] = None
        self._model_name = _resolve_model_name(config_manager)
        self._backend: Optional[str] = None
        self._initialize()

    def is_available(self) -> bool:
        """Check whether any Gemini backend initialized correctly."""
        return self._backend is not None

    def _initialize(self) -> None:
        """Initialize Gemini client."""
        api_key = _resolve_api_key()
        if not api_key:
            return

        # Preferred SDK: google-genai
        try:
            from google import genai

            self._client = genai.Client(api_key=api_key)
            self._backend = "google-genai"
            return
        except ImportError:
            pass
        except Exception:
            pass

        # Backward-compatible fallback: google-generativeai (deprecated upstream).
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=api_key)
            self._legacy_model = legacy_genai.GenerativeModel(self._model_name)
            self._backend = "google-generativeai"
        except Exception:
            self._client = None
            self._legacy_model = None
            self._backend = None

    async def generate_response(self, prompt: str) -> Optional[str]:
        """Generate response using Gemini."""
        if not self.is_available():
            return None

        try:
            loop = asyncio.get_event_loop()
            if self._backend == "google-genai" and self._client is not None:
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.models.generate_content(
                        model=self._model_name,
                        contents=prompt,
                    ),
                )
                return getattr(response, "text", None)

            if self._backend == "google-generativeai" and self._legacy_model is not None:
                response = await loop.run_in_executor(
                    None,
                    lambda: self._legacy_model.generate_content(prompt),
                )
                return getattr(response, "text", None)

            return None
        except Exception:
            return None
