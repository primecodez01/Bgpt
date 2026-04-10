"""
Configuration Manager - Handle settings and credentials.
"""

import json
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

class ConfigManager:
    """Configuration management system."""

    PROVIDER_ALIASES = {
        "gemini": "gemini",
        "google": "gemini",
        "openai": "openai",
        "gpt4": "openai",
        "gpt-4": "openai",
        "gpt3.5": "openai",
        "gpt-3.5": "openai",
        "anthropic": "anthropic",
        "claude": "anthropic",
        "local": "local",
        "ollama": "local",
    }

    THEME_OPTIONS = {"default", "dark", "light", "hacker", "minimal"}
    PROFILE_OPTIONS = {"default", "sunset", "matrix", "midnight", "minimal"}
    PROMPT_STYLES = {"arrow", "classic", "minimal"}
    SAFETY_OPTIONS = {"low", "medium", "high"}
    AGENTIC_RISK_OPTIONS = {"low", "medium"}
    MODEL_DEFAULTS = {
        "gemini": "gemini-2.5-flash",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-latest",
        "local": "tinyllama",
    }
    MODEL_OPTIONS = {
        "gemini": [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
        ],
        "openai": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
        ],
        "anthropic": [
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-opus-latest",
        ],
        "local": [
            "tinyllama",
            "phi3:mini",
            "llama3.2:1b",
            "qwen2:0.5b",
        ],
    }

    _DEFAULT_CONFIG: Dict[str, Any] = {
        "provider": "gemini",
        "theme": "default",
        "safety_level": "medium",
        "auto_execute": False,
        "agentic_mode": False,
        "show_command_details": True,
        "agentic_auto_execute_max_risk": "low",
        "save_history": True,
        "command_timeout": 60,
        "enabled_plugins": [],
        "models": dict(MODEL_DEFAULTS),
        "ui": {
            "profile": "default",
            "prompt_style": "arrow",
            "compact_mode": False,
            "show_timestamps": True,
            "show_tips": True,
            "command_preview_lines": 12,
        },
    }

    _API_KEY_ENV_MAP = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    
    def __init__(self) -> None:
        self.config_dir = Path.home() / ".bgpt"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("bgpt.config")
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with self.config_file.open("r", encoding="utf-8") as config_handle:
                    loaded = json.load(config_handle)
                return self._normalize_config(loaded)
            except Exception as error:
                self.logger.warning("Failed to load config file, using defaults: %s", error)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration."""
        # Use JSON round-trip for a deep copy without mutating class constants.
        return json.loads(json.dumps(self._DEFAULT_CONFIG))

    def _normalize_config(self, raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and merge a user config over defaults."""
        merged = self._default_config()

        for key, value in raw_config.items():
            if key == "ui" and isinstance(value, dict):
                merged["ui"].update(value)
            else:
                merged[key] = value

        normalized_provider = self.normalize_provider(str(merged.get("provider", "gemini")))
        merged["provider"] = normalized_provider or "gemini"

        merged["theme"] = str(merged.get("theme", "default")).lower()
        if merged["theme"] not in self.THEME_OPTIONS:
            merged["theme"] = "default"

        merged["safety_level"] = str(merged.get("safety_level", "medium")).lower()
        if merged["safety_level"] not in self.SAFETY_OPTIONS:
            merged["safety_level"] = "medium"

        timeout = merged.get("command_timeout", 60)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 60
        merged["command_timeout"] = min(max(timeout, 5), 600)

        merged["auto_execute"] = bool(merged.get("auto_execute", False))
        merged["agentic_mode"] = bool(merged.get("agentic_mode", False))
        merged["show_command_details"] = bool(merged.get("show_command_details", True))

        agentic_max_risk = str(merged.get("agentic_auto_execute_max_risk", "low")).lower()
        if agentic_max_risk not in self.AGENTIC_RISK_OPTIONS:
            agentic_max_risk = "low"
        merged["agentic_auto_execute_max_risk"] = agentic_max_risk

        merged["save_history"] = bool(merged.get("save_history", True))

        enabled_plugins = merged.get("enabled_plugins", [])
        if isinstance(enabled_plugins, list):
            merged["enabled_plugins"] = sorted({str(item).strip().lower() for item in enabled_plugins if item})
        else:
            merged["enabled_plugins"] = []

        raw_models = merged.get("models", {})
        if not isinstance(raw_models, dict):
            raw_models = {}

        normalized_models: Dict[str, str] = {}
        for provider_name, default_model in self.MODEL_DEFAULTS.items():
            model_value = raw_models.get(provider_name, default_model)
            if not isinstance(model_value, str) or not model_value.strip():
                model_value = default_model
            normalized_models[provider_name] = model_value.strip()
        merged["models"] = normalized_models

        ui_config = merged.get("ui", {})
        if not isinstance(ui_config, dict):
            ui_config = {}

        profile = str(ui_config.get("profile", "default")).lower()
        if profile not in self.PROFILE_OPTIONS:
            profile = "default"
        ui_config["profile"] = profile

        prompt_style = str(ui_config.get("prompt_style", "arrow")).lower()
        if prompt_style not in self.PROMPT_STYLES:
            prompt_style = "arrow"
        ui_config["prompt_style"] = prompt_style

        ui_config["compact_mode"] = bool(ui_config.get("compact_mode", False))
        ui_config["show_timestamps"] = bool(ui_config.get("show_timestamps", True))
        ui_config["show_tips"] = bool(ui_config.get("show_tips", True))

        preview_lines = ui_config.get("command_preview_lines", 12)
        try:
            preview_lines = int(preview_lines)
        except (TypeError, ValueError):
            preview_lines = 12
        ui_config["command_preview_lines"] = min(max(preview_lines, 3), 30)

        merged["ui"] = ui_config
        return merged
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        temp_file = self.config_file.with_suffix(".tmp")
        with temp_file.open("w", encoding="utf-8") as config_handle:
            json.dump(self._config, config_handle, indent=2)
        temp_file.replace(self.config_file)

    def normalize_provider(self, provider: str) -> Optional[str]:
        """Normalize provider aliases to canonical names."""
        cleaned = provider.strip().lower()
        return self.PROVIDER_ALIASES.get(cleaned)

    def get_config(self) -> Dict[str, Any]:
        """Get a copy of current configuration."""
        return json.loads(json.dumps(self._config))
    
    def get_provider(self) -> str:
        """Get current AI provider."""
        provider = self._config.get("provider", "gemini")
        normalized = self.normalize_provider(str(provider))
        return normalized or "gemini"
    
    def set_provider(self, provider: str) -> None:
        """Set AI provider."""
        normalized = self.normalize_provider(provider)
        if not normalized:
            valid_values = ", ".join(sorted({value for value in self.PROVIDER_ALIASES.values()}))
            raise ValueError(f"Invalid provider '{provider}'. Valid values: {valid_values}")

        self._config["provider"] = normalized
        self._save_config()

    def get_provider_model(self, provider: str) -> str:
        """Get configured model for a provider."""
        normalized = self.normalize_provider(provider)
        if not normalized:
            raise ValueError(f"Invalid provider '{provider}'")

        models = self._config.get("models", {})
        if isinstance(models, dict):
            model = models.get(normalized)
            if isinstance(model, str) and model.strip():
                return model.strip()

        return self.MODEL_DEFAULTS[normalized]

    def set_provider_model(self, provider: str, model: str) -> None:
        """Set model name for a provider."""
        normalized = self.normalize_provider(provider)
        if not normalized:
            raise ValueError(f"Invalid provider '{provider}'")

        cleaned_model = model.strip()
        if not cleaned_model:
            raise ValueError("Model name cannot be empty")

        models = self._config.setdefault("models", {})
        if not isinstance(models, dict):
            models = {}
            self._config["models"] = models

        models[normalized] = cleaned_model
        self._save_config()

    def get_provider_model_options(self, provider: str) -> List[str]:
        """Get recommended model options for a provider."""
        normalized = self.normalize_provider(provider)
        if not normalized:
            raise ValueError(f"Invalid provider '{provider}'")
        return list(self.MODEL_OPTIONS.get(normalized, []))
    
    def set_theme(self, theme: str) -> None:
        """Set UI theme."""
        theme_value = theme.strip().lower()
        if theme_value not in self.THEME_OPTIONS:
            valid_values = ", ".join(sorted(self.THEME_OPTIONS))
            raise ValueError(f"Invalid theme '{theme}'. Valid values: {valid_values}")

        self._config["theme"] = theme_value
        self._save_config()
    
    def set_safety_level(self, level: str) -> None:
        """Set safety level."""
        level_value = level.strip().lower()
        if level_value not in self.SAFETY_OPTIONS:
            valid_values = ", ".join(sorted(self.SAFETY_OPTIONS))
            raise ValueError(f"Invalid safety level '{level}'. Valid values: {valid_values}")

        self._config["safety_level"] = level_value
        self._save_config()

    def get_command_timeout(self) -> int:
        """Get command execution timeout (seconds)."""
        return int(self._config.get("command_timeout", 60))

    def set_command_timeout(self, timeout_seconds: int) -> None:
        """Set command execution timeout in seconds."""
        timeout = min(max(int(timeout_seconds), 5), 600)
        self._config["command_timeout"] = timeout
        self._save_config()

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a top-level boolean config value."""
        return bool(self._config.get(key, default))

    def set_bool(self, key: str, value: bool) -> None:
        """Set a top-level boolean config value."""
        self._config[key] = bool(value)
        self._save_config()

    def get_agentic_auto_execute_max_risk(self) -> str:
        """Get max risk level that agentic mode can auto-execute."""
        value = str(self._config.get("agentic_auto_execute_max_risk", "low")).lower()
        if value not in self.AGENTIC_RISK_OPTIONS:
            return "low"
        return value

    def set_agentic_auto_execute_max_risk(self, risk_level: str) -> None:
        """Set max risk level that agentic mode can auto-execute."""
        normalized = risk_level.strip().lower()
        if normalized not in self.AGENTIC_RISK_OPTIONS:
            valid_values = ", ".join(sorted(self.AGENTIC_RISK_OPTIONS))
            raise ValueError(
                f"Invalid agentic risk level '{risk_level}'. Valid values: {valid_values}"
            )
        self._config["agentic_auto_execute_max_risk"] = normalized
        self._save_config()
    
    def get_theme(self) -> str:
        """Get current theme."""
        return self._config.get("theme", "default")
    
    def get_safety_level(self) -> str:
        """Get current safety level."""
        return self._config.get("safety_level", "medium")

    def get_ui_settings(self) -> Dict[str, Any]:
        """Get terminal UI customization settings."""
        ui_settings = self._config.get("ui", {})
        return dict(ui_settings) if isinstance(ui_settings, dict) else {}

    def set_ui_option(self, key: str, value: Any) -> None:
        """Set a UI option with validation."""
        ui_settings = self._config.setdefault("ui", {})

        if key == "profile":
            profile = str(value).lower()
            if profile not in self.PROFILE_OPTIONS:
                valid_values = ", ".join(sorted(self.PROFILE_OPTIONS))
                raise ValueError(f"Invalid profile '{value}'. Valid values: {valid_values}")
            ui_settings[key] = profile
        elif key == "prompt_style":
            prompt_style = str(value).lower()
            if prompt_style not in self.PROMPT_STYLES:
                valid_values = ", ".join(sorted(self.PROMPT_STYLES))
                raise ValueError(f"Invalid prompt style '{value}'. Valid values: {valid_values}")
            ui_settings[key] = prompt_style
        elif key in {"compact_mode", "show_timestamps", "show_tips"}:
            ui_settings[key] = bool(value)
        elif key == "command_preview_lines":
            preview_lines = min(max(int(value), 3), 30)
            ui_settings[key] = preview_lines
        else:
            raise ValueError(f"Unknown UI option '{key}'")

        self._save_config()

    def get_terminal_profile(self) -> str:
        """Get active terminal profile name."""
        return self.get_ui_settings().get("profile", "default")

    def set_terminal_profile(self, profile: str) -> None:
        """Set active terminal profile."""
        self.set_ui_option("profile", profile)

    def get_enabled_plugins(self) -> List[str]:
        """Get enabled plugin names."""
        plugins = self._config.get("enabled_plugins", [])
        return list(plugins) if isinstance(plugins, list) else []

    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a plugin by name."""
        name = plugin_name.strip().lower()
        plugins = set(self.get_enabled_plugins())
        plugins.add(name)
        self._config["enabled_plugins"] = sorted(plugins)
        self._save_config()

    def disable_plugin(self, plugin_name: str) -> None:
        """Disable a plugin by name."""
        name = plugin_name.strip().lower()
        plugins = set(self.get_enabled_plugins())
        plugins.discard(name)
        self._config["enabled_plugins"] = sorted(plugins)
        self._save_config()

    def run_setup_wizard(self) -> None:
        """Run interactive setup wizard."""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.prompt import Confirm, Prompt
            from rich.table import Table

            console = Console()
            console.print(
                Panel(
                    "Configure provider, model, safety, and terminal experience.",
                    title="Bgpt Setup Wizard",
                    border_style="cyan",
                )
            )

            provider_table = Table(title="AI Providers")
            provider_table.add_column("Option", style="cyan")
            provider_table.add_column("Provider", style="white")
            provider_table.add_column("Use case", style="white")

            provider_map = {
                "1": "gemini",
                "2": "openai",
                "3": "anthropic",
                "4": "local",
            }
            provider_table.add_row("1", "gemini", "fast command generation")
            provider_table.add_row("2", "openai", "general reliability")
            provider_table.add_row("3", "anthropic", "high quality explanations")
            provider_table.add_row("4", "local", "offline usage with Ollama")
            console.print(provider_table)

            provider_choice = Prompt.ask(
                "Select provider",
                choices=list(provider_map.keys()),
                default="1",
            )
            provider = provider_map[provider_choice]
            self.set_provider(provider)

            if provider in {"gemini", "openai", "anthropic"}:
                api_key = Prompt.ask(
                    f"Enter {provider} API key (leave blank to skip)",
                    default="",
                    password=True,
                ).strip()
                if api_key:
                    self._store_api_key(provider, api_key)

            model_options = self.get_provider_model_options(provider)
            model_table = Table(title=f"Model Options ({provider})")
            model_table.add_column("Option", style="cyan")
            model_table.add_column("Model", style="white")
            model_table.add_column("Note", style="white")

            for idx, model_name in enumerate(model_options, start=1):
                note = "recommended" if idx == 1 else ""
                model_table.add_row(str(idx), model_name, note)
            model_table.add_row("c", "custom", "enter your own model id")
            console.print(model_table)

            default_model_choice = "1" if model_options else "c"
            model_choice = Prompt.ask(
                "Select model",
                choices=[str(idx) for idx in range(1, len(model_options) + 1)] + ["c"],
                default=default_model_choice,
            )
            if model_choice == "c":
                selected_model = Prompt.ask("Enter custom model id").strip()
                if not selected_model:
                    selected_model = self.MODEL_DEFAULTS[provider]
            else:
                selected_model = model_options[int(model_choice) - 1]
            self.set_provider_model(provider, selected_model)

            profile_map = {
                "1": "default",
                "2": "sunset",
                "3": "matrix",
                "4": "midnight",
                "5": "minimal",
            }
            profile_table = Table(title="Terminal Profile")
            profile_table.add_column("Option", style="cyan")
            profile_table.add_column("Profile", style="white")
            for option, profile_name in profile_map.items():
                profile_table.add_row(option, profile_name)
            console.print(profile_table)
            profile_choice = Prompt.ask("Select profile", choices=list(profile_map.keys()), default="1")
            self.set_terminal_profile(profile_map[profile_choice])

            prompt_map = {"1": "arrow", "2": "classic", "3": "minimal"}
            prompt_table = Table(title="Prompt Style")
            prompt_table.add_column("Option", style="cyan")
            prompt_table.add_column("Style", style="white")
            prompt_table.add_row("1", "arrow (bgpt ->)")
            prompt_table.add_row("2", "classic (bgpt$)")
            prompt_table.add_row("3", "minimal (>)")
            console.print(prompt_table)
            prompt_choice = Prompt.ask("Select prompt style", choices=list(prompt_map.keys()), default="1")
            self.set_ui_option("prompt_style", prompt_map[prompt_choice])

            theme_map = {
                "1": "default",
                "2": "dark",
                "3": "light",
                "4": "hacker",
                "5": "minimal",
            }
            theme_table = Table(title="Base Theme")
            theme_table.add_column("Option", style="cyan")
            theme_table.add_column("Theme", style="white")
            for option, theme_name in theme_map.items():
                theme_table.add_row(option, theme_name)
            console.print(theme_table)
            theme_choice = Prompt.ask("Select theme", choices=list(theme_map.keys()), default="1")
            self.set_theme(theme_map[theme_choice])

            safety_map = {"1": "low", "2": "medium", "3": "high"}
            safety_table = Table(title="Safety Level")
            safety_table.add_column("Option", style="cyan")
            safety_table.add_column("Level", style="white")
            safety_table.add_column("Behavior", style="white")
            safety_table.add_row("1", "low", "fewer confirmations")
            safety_table.add_row("2", "medium", "balanced checks")
            safety_table.add_row("3", "high", "strict confirmations")
            console.print(safety_table)
            safety_choice = Prompt.ask("Select safety level", choices=list(safety_map.keys()), default="2")
            self.set_safety_level(safety_map[safety_choice])

            timeout_default = str(self.get_command_timeout())
            timeout_raw = Prompt.ask("Command timeout in seconds", default=timeout_default)
            try:
                timeout = int(timeout_raw)
            except ValueError:
                timeout = 60
            self.set_command_timeout(timeout)

            compact_mode = Confirm.ask("Enable compact mode", default=False)
            self.set_ui_option("compact_mode", compact_mode)

            show_timestamps = Confirm.ask("Show timestamps", default=True)
            self.set_ui_option("show_timestamps", show_timestamps)

            show_tips = Confirm.ask("Show onboarding tips", default=True)
            self.set_ui_option("show_tips", show_tips)

            auto_execute = Confirm.ask("Auto execute low-risk commands", default=False)
            self.set_bool("auto_execute", auto_execute)

            agentic_mode = Confirm.ask("Enable agentic decision mode", default=True)
            self.set_bool("agentic_mode", agentic_mode)

            if agentic_mode:
                risk_table = Table(title="Agentic Auto-Execution Risk")
                risk_table.add_column("Option", style="cyan")
                risk_table.add_column("Max risk", style="white")
                risk_table.add_column("Behavior", style="white")
                risk_table.add_row("1", "low", "auto-run only low-risk commands")
                risk_table.add_row("2", "medium", "auto-run low and medium risk")
                console.print(risk_table)
                risk_choice = Prompt.ask(
                    "Select max risk for auto execution",
                    choices=["1", "2"],
                    default="1",
                )
                risk_map = {"1": "low", "2": "medium"}
                self.set_agentic_auto_execute_max_risk(risk_map[risk_choice])

            show_details = Confirm.ask(
                "Show full command details before execution",
                default=not agentic_mode,
            )
            self.set_bool("show_command_details", show_details)

            save_history = Confirm.ask("Save command history", default=True)
            self.set_bool("save_history", save_history)

            summary = Table(title="Setup Summary")
            summary.add_column("Setting", style="cyan")
            summary.add_column("Value", style="white")
            summary.add_row("Provider", provider)
            summary.add_row("Model", self.get_provider_model(provider))
            summary.add_row("Profile", self.get_terminal_profile())
            summary.add_row("Prompt style", self.get_ui_settings().get("prompt_style", "arrow"))
            summary.add_row("Theme", self.get_theme())
            summary.add_row("Safety", self.get_safety_level())
            summary.add_row("Timeout", f"{self.get_command_timeout()}s")
            summary.add_row("Compact mode", "on" if compact_mode else "off")
            summary.add_row("Timestamps", "on" if show_timestamps else "off")
            summary.add_row("Tips", "on" if show_tips else "off")
            summary.add_row("Auto execute", "on" if auto_execute else "off")
            summary.add_row("Agentic mode", "on" if agentic_mode else "off")
            summary.add_row(
                "Agentic max risk",
                self.get_agentic_auto_execute_max_risk(),
            )
            summary.add_row("Show command details", "on" if show_details else "off")
            summary.add_row("History", "on" if save_history else "off")
            console.print(summary)
            console.print(Panel("Setup complete.", border_style="green"))

        except Exception:
            self._run_basic_setup_wizard()

    def _run_basic_setup_wizard(self) -> None:
        """Fallback setup wizard when rich is unavailable."""
        print("Bgpt Setup Wizard")
        print("=================")

        print("\nChoose AI provider:")
        print("1. gemini")
        print("2. openai")
        print("3. anthropic")
        print("4. local")

        provider_map = {"1": "gemini", "2": "openai", "3": "anthropic", "4": "local"}
        provider_choice = input("Enter choice [1]: ").strip() or "1"
        provider = provider_map.get(provider_choice, "gemini")
        self.set_provider(provider)

        if provider in {"gemini", "openai", "anthropic"}:
            api_key = input(f"Enter {provider} API key (or press Enter to skip): ").strip()
            if api_key:
                self._store_api_key(provider, api_key)

        model_options = self.get_provider_model_options(provider)
        print(f"\nChoose model for {provider}:")
        for idx, model_name in enumerate(model_options, start=1):
            print(f"{idx}. {model_name}")
        print("c. custom")
        default_model_choice = "1" if model_options else "c"
        model_choice = input(f"Enter choice [{default_model_choice}]: ").strip() or default_model_choice
        if model_choice == "c":
            selected_model = input("Enter custom model id: ").strip() or self.MODEL_DEFAULTS[provider]
        else:
            try:
                selected_model = model_options[int(model_choice) - 1]
            except (ValueError, IndexError):
                selected_model = self.MODEL_DEFAULTS[provider]
        self.set_provider_model(provider, selected_model)

        print("\nChoose terminal profile:")
        print("1. default")
        print("2. sunset")
        print("3. matrix")
        print("4. midnight")
        print("5. minimal")
        profile_map = {
            "1": "default",
            "2": "sunset",
            "3": "matrix",
            "4": "midnight",
            "5": "minimal",
        }
        profile_choice = input("Enter choice [1]: ").strip() or "1"
        self.set_terminal_profile(profile_map.get(profile_choice, "default"))

        print("\nChoose prompt style:")
        print("1. arrow")
        print("2. classic")
        print("3. minimal")
        prompt_map = {"1": "arrow", "2": "classic", "3": "minimal"}
        prompt_choice = input("Enter choice [1]: ").strip() or "1"
        self.set_ui_option("prompt_style", prompt_map.get(prompt_choice, "arrow"))

        print("\nChoose base theme:")
        print("1. default")
        print("2. dark")
        print("3. light")
        print("4. hacker")
        print("5. minimal")
        theme_map = {
            "1": "default",
            "2": "dark",
            "3": "light",
            "4": "hacker",
            "5": "minimal",
        }
        theme_choice = input("Enter choice [1]: ").strip() or "1"
        self.set_theme(theme_map.get(theme_choice, "default"))

        print("\nChoose safety level:")
        print("1. low")
        print("2. medium")
        print("3. high")
        safety_map = {"1": "low", "2": "medium", "3": "high"}
        safety_choice = input("Enter choice [2]: ").strip() or "2"
        self.set_safety_level(safety_map.get(safety_choice, "medium"))

        timeout_choice = input("\nCommand timeout in seconds [60]: ").strip() or "60"
        try:
            timeout = int(timeout_choice)
        except ValueError:
            timeout = 60
        self.set_command_timeout(timeout)

        compact_choice = input("Enable compact mode? [y/N]: ").strip().lower()
        self.set_ui_option("compact_mode", compact_choice in {"y", "yes"})

        timestamp_choice = input("Show timestamps? [Y/n]: ").strip().lower()
        self.set_ui_option("show_timestamps", timestamp_choice not in {"n", "no"})

        tips_choice = input("Show onboarding tips? [Y/n]: ").strip().lower()
        self.set_ui_option("show_tips", tips_choice not in {"n", "no"})

        auto_exec_choice = input("Auto execute low-risk commands? [y/N]: ").strip().lower()
        self.set_bool("auto_execute", auto_exec_choice in {"y", "yes"})

        agentic_choice = input("Enable agentic decision mode? [Y/n]: ").strip().lower()
        agentic_mode = agentic_choice not in {"n", "no"}
        self.set_bool("agentic_mode", agentic_mode)

        if agentic_mode:
            print("\nAgentic auto-execution max risk:")
            print("1. low")
            print("2. medium")
            risk_choice = input("Enter choice [1]: ").strip() or "1"
            risk_map = {"1": "low", "2": "medium"}
            self.set_agentic_auto_execute_max_risk(risk_map.get(risk_choice, "low"))

        show_details_choice = input("Show full command details? [y/N]: ").strip().lower()
        self.set_bool("show_command_details", show_details_choice in {"y", "yes"})

        history_choice = input("Save command history? [Y/n]: ").strip().lower()
        self.set_bool("save_history", history_choice not in {"n", "no"})

        print("\nSetup complete.")
    
    def _store_api_key(self, provider: str, api_key: str) -> None:
        """Store API key securely."""
        try:
            import keyring
            keyring.set_password("bgpt", provider, api_key)
            print(f"{provider} API key stored securely")
        except Exception:
            # Fallback to environment variable suggestion
            env_var = self._API_KEY_ENV_MAP.get(provider, f"{provider.upper()}_API_KEY")
            print(f"Could not use keyring. Set {env_var} in your shell environment.")
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider."""
        normalized = self.normalize_provider(provider) or provider
        try:
            import keyring
            key = keyring.get_password("bgpt", normalized)
            if key:
                return key
        except Exception:
            pass

        env_var = self._API_KEY_ENV_MAP.get(normalized)
        if env_var:
            return os.getenv(env_var)
        return None
    
    def show_config(self) -> None:
        """Display current configuration."""
        print("Current Configuration:")
        print("=" * 20)
        print(json.dumps(self._config, indent=2))
    
    def run_diagnostics(self) -> None:
        """Run system diagnostics."""
        print("System Diagnostics")
        print("=" * 20)
        
        # Check Python version
        import sys
        print(f"Python: {sys.version}")
        
        # Check core dependencies
        deps = {
            "rich": "Terminal UI",
            "click": "CLI framework",
            "google.genai": "Gemini support (preferred)",
            "google.generativeai": "Gemini support (legacy)",
            "openai": "OpenAI support",
            "anthropic": "Anthropic support",
            "ollama": "Local model support",
            "mcp": "MCP SDK (optional)",
        }

        import importlib
        import warnings
        
        for dep, description in deps.items():
            try:
                if dep == "google.generativeai":
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", FutureWarning)
                        importlib.import_module(dep)
                else:
                    importlib.import_module(dep)
                print(f"OK  {dep}: installed ({description})")
            except ImportError:
                print(f"MISS {dep}: not installed ({description})")
        
        # Check API keys
        providers = ["gemini", "openai", "anthropic"]
        for provider in providers:
            key = self.get_api_key(provider)
            status = "configured" if key else "not configured"
            print(f"KEY {provider}: {status}")
