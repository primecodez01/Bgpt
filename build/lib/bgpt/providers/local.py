"""
Local Provider - Local LLM integration (Ollama).
"""

import asyncio
import os
from typing import Any, Optional


def _resolve_model_name(config_manager: Optional[Any]) -> str:
    """Resolve local model from config first, then env, then default."""
    if config_manager is not None:
        try:
            model_from_config = config_manager.get_provider_model("local")
            if model_from_config:
                return model_from_config
        except Exception:
            pass

    return os.getenv("BGPT_LOCAL_MODEL", "tinyllama")

class LocalProvider:
    """Local LLM provider using Ollama."""

    def __init__(self, config_manager: Optional[Any] = None) -> None:
        self._config_manager = config_manager
        self._client = None
        self._model_cache = None
        self._preferred_model = _resolve_model_name(config_manager)
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize local client."""
        try:
            import ollama
            self._client = ollama
            # Remove all logging - silent initialization
        except ImportError:
            # Silently fail if ollama not installed
            pass
        except Exception:
            # Silently fail on any other errors
            pass
    
    async def _pull_model(self, model: str) -> bool:
        """Download/pull a model if not available."""
        if not self._client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.pull(model)
            )
            return True
        except Exception:
            return False
    
    async def _check_model_available(self, model: str) -> bool:
        """Check if a model is downloaded and available."""
        if not self._client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            models = await loop.run_in_executor(
                None,
                lambda: self._client.list()
            )
            available_models = [m['name'] for m in models.get('models', [])]
            return model in available_models
        except Exception:
            return False
    
    async def _test_model(self, model: str) -> bool:
        """Test if a model can generate responses."""
        if not self._client:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.generate(
                    model=model,
                    prompt="Hi",
                    options={'num_predict': 1}  # Generate only 1 token for testing
                )
            )
            return bool(response.get('response'))
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Check if local provider is available."""
        return self._client is not None
    
    async def ensure_model_ready(self) -> Optional[str]:
        """Ensure at least one model is ready for use."""
        if not self._client:
            return None

        # Return cached model if available
        if self._model_cache:
            if await self._test_model(self._model_cache):
                return self._model_cache

        # Honor preferred model from config when available.
        if self._preferred_model:
            if await self._check_model_available(self._preferred_model):
                if await self._test_model(self._preferred_model):
                    self._model_cache = self._preferred_model
                    return self._model_cache
            else:
                # If user selected a preferred model, attempt pull once.
                if await self._pull_model(self._preferred_model):
                    if await self._test_model(self._preferred_model):
                        self._model_cache = self._preferred_model
                        return self._model_cache
        
        # Check what models are available locally
        try:
            models = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.list()
            )
            available_models = models.get('models', [])

            if not available_models:
                # No models installed, try to setup quietly.
                return await self._auto_setup_model()

            # Try available models first
            for model_info in available_models:
                model_name = model_info['name']
                if await self._test_model(model_name):
                    self._model_cache = model_name
                    return model_name

        except Exception:
            pass

        # Try smallest models if none working
        models_to_try = ["tinyllama", "phi3:mini", "llama3.2:1b", "qwen2:0.5b"]

        for model in models_to_try:
            if await self._check_model_available(model):
                if await self._test_model(model):
                    self._model_cache = model
                    return model

        return None
    
    async def _auto_setup_model(self) -> Optional[str]:
        """Auto-setup the smallest model if none exist."""
        try:
            if await self._pull_model("tinyllama"):
                if await self._test_model("tinyllama"):
                    self._model_cache = "tinyllama"
                    return "tinyllama"
        except Exception:
            pass

        return None
    
    def get_models_info(self) -> dict:
        """Get information about available models."""
        if not self._client:
            return {"status": "unavailable", "reason": "Ollama not installed"}
        
        try:
            models = self._client.list()
            return {
                "status": "available",
                "models": models.get('models', []),
                "storage_path": "~/.ollama/models"
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}
    
    async def setup_if_needed(self) -> bool:
        """Setup local provider if Ollama is available but no models exist."""
        if not self._client:
            return False

        # Check if we already have a working model
        if await self.ensure_model_ready():
            return True

        # Try to auto-setup tinyllama
        try:
            if await self._pull_model("tinyllama"):
                self._model_cache = "tinyllama"
                return True
        except Exception:
            pass

        return False
    
    async def generate_response(self, prompt: str) -> Optional[str]:
        """Generate response using local model."""
        if not self._client:
            return None

        try:
            # Ensure we have a working model
            working_model = await self.ensure_model_ready()
            if not working_model:
                return None

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            response = await loop.run_in_executor(
                None,
                lambda: self._client.generate(
                    model=working_model,
                    prompt=prompt
                )
            )
            return response['response']
        except Exception:
            return None
