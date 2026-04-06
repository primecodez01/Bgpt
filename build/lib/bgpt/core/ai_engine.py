"""
AI Engine - Multi-provider AI integration for command generation.

This module provides an abstraction layer for different AI providers
including Gemini, OpenAI, Claude, and local models.
"""

import asyncio
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config.manager import ConfigManager
from ..utils.logger import get_logger

# Import providers with fallback
try:
    from ..providers.gemini import GeminiProvider
except ImportError:
    GeminiProvider = None

try:
    from ..providers.openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from ..providers.anthropic import AnthropicProvider
except ImportError:
    AnthropicProvider = None

try:
    from ..providers.local import LocalProvider
except ImportError:
    LocalProvider = None

logger = get_logger(__name__)


class SafetyLevel(Enum):
    """Safety levels for command execution."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CommandResult:
    """Result of AI command generation."""
    command: str
    explanation: str
    safety_level: SafetyLevel
    requires_sudo: bool
    destructive: bool
    alternatives: List[str]
    prerequisites: List[str]
    confidence: float
    provider_used: str


class AIEngine:
    """Multi-provider AI engine for command generation."""
    
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        self.providers = self._initialize_providers()
        self.context = self._gather_system_context()
        
    def _initialize_providers(self) -> Dict[str, Any]:
        """Initialize available AI providers."""
        providers = {}

        if GeminiProvider:
            try:
                provider = GeminiProvider(self.config_manager)
                if self._provider_ready(provider):
                    providers['gemini'] = provider
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")

        if OpenAIProvider:
            try:
                provider = OpenAIProvider(self.config_manager)
                if self._provider_ready(provider):
                    providers['openai'] = provider
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")

        if AnthropicProvider:
            try:
                provider = AnthropicProvider(self.config_manager)
                if self._provider_ready(provider):
                    providers['anthropic'] = provider
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")

        if LocalProvider:
            try:
                provider = LocalProvider(self.config_manager)
                if self._provider_ready(provider):
                    providers['local'] = provider
            except Exception as e:
                logger.warning(f"Failed to initialize Local provider: {e}")

        # Fallback provider if no AI providers are available
        if not providers:
            providers['fallback'] = FallbackProvider()
            logger.warning("No AI providers available, using fallback")

        return providers

    @staticmethod
    def _provider_ready(provider: Any) -> bool:
        """Check whether a provider instance is usable."""
        try:
            if hasattr(provider, "is_available"):
                return bool(provider.is_available())
            return getattr(provider, "_client", None) is not None
        except Exception:
            return False
    
    def _gather_system_context(self) -> Dict[str, Any]:
        """Gather system context for better command generation."""
        try:
            return {
                'os': platform.system(),
                'os_version': platform.release(),
                'architecture': platform.machine(),
                'shell': os.environ.get('SHELL', '/bin/bash'),
                'user': os.environ.get('USER', 'unknown'),
                'cwd': os.getcwd(),
                'python_version': platform.python_version(),
                'available_commands': self._get_available_commands(),
            }
        except Exception as e:
            logger.error(f"Error gathering system context: {e}")
            return {}
    
    def _get_available_commands(self) -> List[str]:
        """Get list of available system commands."""
        commands: List[str] = []

        # Best effort: use bash builtins when available.
        try:
            result = subprocess.run(
                ["bash", "-lc", "compgen -c"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                commands.extend(result.stdout.splitlines())
        except Exception:
            pass

        # Fallback: discover executables from PATH.
        if not commands:
            try:
                for path_entry in os.environ.get("PATH", "").split(os.pathsep):
                    if not path_entry or not os.path.isdir(path_entry):
                        continue
                    for name in os.listdir(path_entry):
                        full_path = os.path.join(path_entry, name)
                        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                            commands.append(name)
            except Exception:
                pass

        # Return unique entries while preserving order.
        unique_commands = list(dict.fromkeys(commands))
        return unique_commands[:200]
    
    def _build_prompt(self, query: str, recent_history: Optional[List[str]] = None) -> str:
        """Build the AI prompt with context."""
        context_str = f"""
System Context:
- OS: {self.context.get('os', 'Unknown')} {self.context.get('os_version', '')}
- Architecture: {self.context.get('architecture', 'Unknown')}
- Shell: {self.context.get('shell', '/bin/bash')}
- Working Directory: {self.context.get('cwd', '/')}
- User: {self.context.get('user', 'unknown')}
"""
        
        if recent_history:
            context_str += f"\nRecent Commands:\n" + "\n".join(recent_history[-5:])
        
        prompt = f"""You are Bgpt, an expert system administrator and shell command specialist.

{context_str}

Request: "{query}"

Generate a safe, efficient shell command following this exact JSON format:

{{
    "command": "[exact shell command]",
    "explanation": "[brief explanation of what it does]",
    "safety_level": "[LOW/MEDIUM/HIGH]",
    "requires_sudo": "[true/false]",
    "destructive": "[true/false]",
    "alternatives": ["alternative approach 1", "alternative approach 2"],
    "prerequisites": ["required tool/package 1", "required tool/package 2"],
    "confidence": "[0.0-1.0]"
}}

Rules:
- Return JSON only, without markdown fences.
- Keep the command compatible with the detected operating system.
- Prefer non-destructive commands whenever possible.

Safety Guidelines:
- Never suggest commands that could harm the system
- Always prefer safer alternatives when available
- Flag destructive operations clearly
- Suggest backups for risky operations
- Use appropriate safety levels: LOW for safe commands, MEDIUM for system changes, HIGH for destructive operations
- For install/uninstall tasks, use the package manager that matches the operating system and request context
- Do not use force flags unless explicitly requested by the user
"""
        return prompt
    
    async def generate_command(self, query: str, recent_history: Optional[List[str]] = None) -> Optional[CommandResult]:
        """Generate a command using the configured AI provider."""
        prompt = self._build_prompt(query, recent_history)
        
        # Get preferred provider
        preferred_provider = self.config_manager.get_provider()
        
        # Try providers in order of preference
        provider_order = [preferred_provider] + [
            p for p in self.providers.keys() if p != preferred_provider
        ]
        
        for provider_name in provider_order:
            if provider_name not in self.providers:
                continue
                
            try:
                logger.info(f"Trying provider: {provider_name}")
                provider = self.providers[provider_name]
                
                response = await provider.generate_response(prompt)
                if response:
                    result = self._parse_response(response, provider_name)
                    if result:
                        logger.info(f"Successfully generated command using {provider_name}")
                        return result
                        
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        logger.error("All providers failed to generate a command")
        return None
    
    def _parse_response(self, response: str, provider_name: str) -> Optional[CommandResult]:
        """Parse AI response into CommandResult."""
        try:
            text = response.strip()

            # Strip markdown code fences if present.
            if text.startswith("```"):
                lines = text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines).strip()

            start = text.find("{")
            end = text.rfind("}")

            if start == -1 or end == -1 or end < start:
                logger.warning("Provider %s returned non-JSON response", provider_name)
                return None

            data = json.loads(text[start : end + 1])

            command = str(data.get("command", "")).strip()
            if not command:
                return None

            explanation = str(data.get("explanation", "")).strip()
            safety_raw = str(data.get("safety_level", "medium")).lower()
            try:
                safety_level = SafetyLevel(safety_raw)
            except ValueError:
                safety_level = SafetyLevel.MEDIUM

            requires_sudo = self._to_bool(data.get("requires_sudo", False))
            destructive = self._to_bool(data.get("destructive", False))
            alternatives = self._to_list(data.get("alternatives", []))
            prerequisites = self._to_list(data.get("prerequisites", []))
            confidence = self._to_confidence(data.get("confidence", 0.7))

            return CommandResult(
                command=command,
                explanation=explanation,
                safety_level=safety_level,
                requires_sudo=requires_sudo,
                destructive=destructive,
                alternatives=alternatives,
                prerequisites=prerequisites,
                confidence=confidence,
                provider_used=provider_name,
            )

        except Exception as e:
            logger.error(f"Failed to parse response: {e}")

        return None

    @staticmethod
    def _to_bool(value: Any) -> bool:
        """Convert provider output value to bool safely."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        if isinstance(value, (int, float)):
            return value != 0
        return False

    @staticmethod
    def _to_list(value: Any) -> List[str]:
        """Convert provider output value to list of strings."""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return []
            return [cleaned]
        return []

    @staticmethod
    def _to_confidence(value: Any) -> float:
        """Convert provider confidence value to normalized float [0, 1]."""
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.7
        return max(0.0, min(numeric, 1.0))
    
    async def explain_command(self, command: str) -> None:
        """Explain an existing command."""
        prompt = f"""Explain this shell command in detail:

Command: {command}

Provide a comprehensive explanation including:
1. What the command does
2. Each part/flag explained
3. Potential risks or side effects
4. Common use cases
5. Alternative approaches

Format as clear, structured text suitable for terminal display.
"""
        
        preferred_provider = self.config_manager.get_provider()
        provider_order = [preferred_provider] + [
            name for name in self.providers.keys() if name != preferred_provider
        ]

        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            try:
                response = await provider.generate_response(prompt)
                if response:
                    print("Command:")
                    print(command)
                    print("\nExplanation:")
                    print(response)
                    return
            except Exception as error:
                logger.error("Failed to explain command using %s: %s", provider_name, error)

        print(f"Could not explain command: {command}")


class FallbackProvider:
    """Fallback provider when no AI services are available."""

    async def generate_response(self, prompt: str) -> Optional[str]:
        """Generate a basic response without AI."""
        if "Explain this shell command in detail" in prompt:
            command = "unknown"
            for line in prompt.splitlines():
                if line.strip().startswith("Command:"):
                    command = line.split("Command:", 1)[1].strip()
                    break
            return (
                f"This command is: {command}\n"
                "Bgpt is running in fallback mode, so detailed AI explanation is unavailable.\n"
                "Install and configure an AI provider (gemini/openai/anthropic/local) for richer breakdowns."
            )

        # Extract the query from prompt
        if 'Request: "' in prompt:
            start = prompt.find('Request: "') + 10
            end = prompt.find('"', start)
            query = prompt[start:end] if end != -1 else "unknown command"
        else:
            query = "unknown command"
        
        # Simple command suggestions based on keywords
        if "list" in query.lower() or "show" in query.lower():
            command = "ls -la"
        elif "uninstall" in query.lower() or "remove" in query.lower():
            words = [part.strip('.,\"\'') for part in query.split()]
            stop_words = {"uninstall", "remove", "delete", "please", "package", "app", "the", "a", "an"}
            candidates = [word for word in words if word and word.lower() not in stop_words]
            package_name = candidates[-1] if candidates else "<package>"
            command = f"sudo apt remove {package_name}"
        elif "find" in query.lower():
            command = "find . -name '*'"
        elif "disk" in query.lower() or "space" in query.lower():
            command = "df -h"
        elif "process" in query.lower():
            command = "ps aux"
        else:
            command = "echo 'Please install an AI provider (gemini, openai, etc.) for better command generation'"
        
        return f'''{{
    "command": "{command}",
    "explanation": "Basic command suggestion (install AI provider for better results)",
    "safety_level": "LOW",
    "requires_sudo": false,
    "destructive": false,
    "alternatives": [],
    "prerequisites": [],
    "confidence": 0.3
}}'''
