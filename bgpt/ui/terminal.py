"""
Terminal UI - Rich terminal interface for Bgpt.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
import importlib
from typing import Any, Dict, Iterable, List


try:
    Console = importlib.import_module("rich.console").Console
    Panel = importlib.import_module("rich.panel").Panel
    prompt_module = importlib.import_module("rich.prompt")
    Prompt = prompt_module.Prompt
    Confirm = prompt_module.Confirm
    Syntax = importlib.import_module("rich.syntax").Syntax
    Table = importlib.import_module("rich.table").Table
except Exception as import_error:  # pragma: no cover - import guard only
    raise RuntimeError("Bgpt requires the 'rich' package for terminal UI rendering.") from import_error


@dataclass(frozen=True)
class UIProfile:
    """Visual profile used by the terminal UI."""

    name: str
    accent: str
    secondary: str
    success: str
    warning: str
    error: str
    border: str
    syntax_theme: str


UI_PROFILES: Dict[str, UIProfile] = {
    "default": UIProfile(
        name="default",
        accent="bright_cyan",
        secondary="cyan",
        success="green",
        warning="yellow",
        error="red",
        border="cyan",
        syntax_theme="monokai",
    ),
    "sunset": UIProfile(
        name="sunset",
        accent="bright_magenta",
        secondary="bright_yellow",
        success="green",
        warning="bright_yellow",
        error="bright_red",
        border="magenta",
        syntax_theme="fruity",
    ),
    "matrix": UIProfile(
        name="matrix",
        accent="bright_green",
        secondary="green",
        success="bright_green",
        warning="yellow",
        error="red",
        border="green",
        syntax_theme="native",
    ),
    "midnight": UIProfile(
        name="midnight",
        accent="bright_blue",
        secondary="cyan",
        success="bright_green",
        warning="yellow",
        error="bright_red",
        border="blue",
        syntax_theme="one-dark",
    ),
    "minimal": UIProfile(
        name="minimal",
        accent="white",
        secondary="bright_black",
        success="green",
        warning="yellow",
        error="red",
        border="white",
        syntax_theme="ansi_dark",
    ),
}

THEME_OVERRIDES: Dict[str, Dict[str, str]] = {
    "default": {},
    "dark": {
        "accent": "bright_blue",
        "secondary": "cyan",
        "border": "blue",
        "syntax_theme": "one-dark",
    },
    "light": {
        "accent": "blue",
        "secondary": "bright_blue",
        "border": "bright_blue",
        "syntax_theme": "emacs",
    },
    "hacker": {
        "accent": "bright_green",
        "secondary": "green",
        "success": "bright_green",
        "warning": "yellow",
        "border": "green",
        "syntax_theme": "native",
    },
    "minimal": {
        "accent": "white",
        "secondary": "bright_black",
        "success": "white",
        "warning": "bright_black",
        "border": "white",
        "syntax_theme": "ansi_dark",
    },
}

class TerminalUI:
    """Rich terminal user interface."""
    
    def __init__(self, console: Any, config_manager: Any) -> None:
        self.console = console
        self.config_manager = config_manager
        self.profile = UI_PROFILES["default"]
        self.ui_settings: Dict[str, Any] = {}
        self._refresh_preferences()

    def _refresh_preferences(self) -> None:
        """Refresh profile and UI settings from config manager."""
        settings = self.config_manager.get_ui_settings()
        profile_name = str(settings.get("profile", "default")).lower()
        theme_name = str(self.config_manager.get_theme()).lower()

        base_profile = UI_PROFILES.get(profile_name, UI_PROFILES["default"])
        overrides = THEME_OVERRIDES.get(theme_name, {})
        self.profile = replace(base_profile, **overrides) if overrides else base_profile
        self.ui_settings = settings

    def _timestamp_prefix(self) -> str:
        """Get timestamp prefix for messages if enabled."""
        if self.ui_settings.get("show_timestamps", True):
            return f"[{datetime.now().strftime('%H:%M:%S')}] "
        return ""

    def _chat_prompt(self) -> str:
        """Build chat prompt label from active prompt style."""
        prompt_style = str(self.ui_settings.get("prompt_style", "arrow")).lower()
        prefix = self._timestamp_prefix()
        if prompt_style == "classic":
            return f"[{self.profile.accent}]{prefix}bgpt$[/]"
        if prompt_style == "minimal":
            return f"[{self.profile.accent}]{prefix}>[/]"
        return f"[{self.profile.accent}]{prefix}bgpt ->[/]"

    def _render_command_preview(self, command: str) -> Any:
        """Render command preview with configured line limit."""
        max_lines = int(self.ui_settings.get("command_preview_lines", 12))
        lines = command.splitlines() or [command]
        if len(lines) > max_lines:
            lines = lines[:max_lines] + ["# ... output truncated ..."]
        preview = "\n".join(lines)
        return Syntax(preview, "bash", theme=self.profile.syntax_theme, line_numbers=False)

    @contextmanager
    def thinking(self, message: str = "Generating command") -> Iterable[None]:
        """Display a non-blocking spinner while a long action runs."""
        self._refresh_preferences()
        status_text = f"[{self.profile.secondary}]{message}[/]"
        with self.console.status(status_text, spinner="dots"):
            yield
    
    def show_welcome(self) -> None:
        """Show welcome message."""
        self._refresh_preferences()
        provider = self.config_manager.get_provider()
        try:
            model = self.config_manager.get_provider_model(provider)
        except Exception:
            model = "default"
        safety_level = self.config_manager.get_safety_level()
        compact = self.ui_settings.get("compact_mode", False)

        body = [
            f"[{self.profile.accent}]Bgpt[/] turns natural language into shell commands.",
            f"Provider: [{self.profile.secondary}]{provider}[/]",
            f"Model: [{self.profile.secondary}]{model}[/]",
            f"Theme: [{self.profile.secondary}]{self.config_manager.get_theme()}[/]",
            f"Safety: [{self.profile.secondary}]{safety_level}[/]",
            f"Profile: [{self.profile.secondary}]{self.profile.name}[/]",
            "Type 'help' for commands or 'exit' to quit.",
        ]
        if not compact and self.ui_settings.get("show_tips", True):
            body.append("Tip: Use '/profile matrix' or '/style classic' during chat.")

        welcome = Panel(
            "\n".join(body),
            title="Bgpt",
            border_style=self.profile.border,
        )
        self.console.print(welcome)
    
    def show_thinking(self) -> None:
        """Backward-compatible thinking hook."""
        self.console.print(
            f"[{self.profile.secondary}]{self._timestamp_prefix()}Working on it...[/]"
        )
    
    def display_command_result(self, command_result: Any, safety_result: Any) -> None:
        """Display generated command with safety info."""
        self._refresh_preferences()

        syntax = self._render_command_preview(command_result.command)
        command_panel = Panel(
            syntax,
            title=f"Generated Command ({command_result.provider_used})",
            border_style=self.profile.success,
        )
        self.console.print(command_panel)

        summary_table = Table(show_header=False, box=None, pad_edge=False)
        summary_table.add_column(style=self.profile.secondary)
        summary_table.add_column(style="white")

        confidence = getattr(command_result, "confidence", 0.0)
        confidence_pct = max(min(float(confidence), 1.0), 0.0) * 100
        try:
            model_name = self.config_manager.get_provider_model(command_result.provider_used)
        except Exception:
            model_name = "n/a"

        summary_table.add_row("Explanation", str(command_result.explanation or "No explanation provided."))
        summary_table.add_row("Model", model_name)
        summary_table.add_row("Confidence", f"{confidence_pct:.0f}%")
        summary_table.add_row("Risk", str(getattr(safety_result.risk_level, "value", "unknown")))
        summary_table.add_row("Confirmation", "required" if safety_result.requires_confirmation else "not required")
        summary_table.add_row("Sandbox", "enabled" if safety_result.sandbox else "disabled")
        self.console.print(summary_table)

        alternatives = getattr(command_result, "alternatives", []) or []
        prerequisites = getattr(command_result, "prerequisites", []) or []
        if alternatives and not self.ui_settings.get("compact_mode", False):
            self.console.print(f"[{self.profile.secondary}]Alternatives:[/]")
            for option in alternatives[:3]:
                self.console.print(f"  - {option}")

        if prerequisites and not self.ui_settings.get("compact_mode", False):
            self.console.print(f"[{self.profile.secondary}]Prerequisites:[/]")
            for prerequisite in prerequisites[:3]:
                self.console.print(f"  - {prerequisite}")

        if safety_result.warnings:
            for warning in safety_result.warnings:
                self.console.print(f"[{self.profile.warning}]Warning: {warning}[/]")
    
    def confirm_execution(self, command_result: Any, safety_result: Any, force: bool = False) -> bool:
        """Ask user to confirm command execution."""
        if not force and not safety_result.requires_confirmation:
            return True

        risk_label = getattr(safety_result.risk_level, "value", "unknown")
        prompt = f"Execute command? (risk: {risk_label})"
        return Confirm.ask(prompt, default=False)
    
    def display_execution_result(self, execution_result: Any) -> None:
        """Display command execution results."""
        self._refresh_preferences()

        status = "success" if execution_result.success else "failed"
        elapsed = f"{execution_result.execution_time:.2f}s"
        header = f"Execution {status} in {elapsed} (exit code: {execution_result.return_code})"

        style = self.profile.success if execution_result.success else self.profile.error
        self.console.print(f"[{style}]{self._timestamp_prefix()}{header}[/]")

        if execution_result.success:
            if execution_result.stdout:
                stdout_panel = Panel(
                    execution_result.stdout.rstrip("\n"),
                    title="stdout",
                    border_style=self.profile.border,
                )
                self.console.print(stdout_panel)
        else:
            if execution_result.stderr:
                stderr_panel = Panel(
                    execution_result.stderr.rstrip("\n"),
                    title="stderr",
                    border_style=self.profile.error,
                )
                self.console.print(stderr_panel)
    
    def show_chat_header(self) -> None:
        """Show chat mode header."""
        self._refresh_preferences()
        compact = self.ui_settings.get("compact_mode", False)
        header = f"[{self.profile.accent}]Chat mode active[/] - Ask for shell commands in plain language."
        self.console.print(header)
        if not compact:
            self.console.print(
                ""
                f"[{self.profile.secondary}]Quick commands:[/] "
                "help, history, /theme <name>, /profile <name>, /model <name>, /agentic on|off"
            )
    
    def get_chat_input(self) -> str:
        """Get user input in chat mode."""
        self._refresh_preferences()
        return Prompt.ask(self._chat_prompt())
    
    def show_goodbye(self) -> None:
        """Show goodbye message."""
        self.console.print(f"[{self.profile.secondary}]Session ended. Goodbye.[/]")
    
    def show_error(self, message: str) -> None:
        """Show error message."""
        self.console.print(f"[{self.profile.error}]Error: {message}[/]")
    
    def show_warning(self, message: str) -> None:
        """Show warning message."""
        self.console.print(f"[{self.profile.warning}]Warning: {message}[/]")
    
    def show_info(self, message: str) -> None:
        """Show info message."""
        self.console.print(f"[{self.profile.secondary}]{self._timestamp_prefix()}{message}[/]")

    def show_success(self, message: str) -> None:
        """Show success message."""
        self.console.print(f"[{self.profile.success}]{self._timestamp_prefix()}{message}[/]")
    
    def show_help(self) -> None:
        """Show help information."""
        help_table = Table(title="Bgpt Commands")
        help_table.add_column("Command", style=self.profile.accent)
        help_table.add_column("Description", style="white")
        
        help_table.add_row("help", "Show this help message")
        help_table.add_row("history", "Show command history")
        help_table.add_row("/theme <name>", "Set theme: default/dark/light/hacker/minimal")
        help_table.add_row("/profile <name>", "Switch profile: default/sunset/matrix/midnight/minimal")
        help_table.add_row("/style <name>", "Set prompt style: arrow/classic/minimal")
        help_table.add_row("/model <name>", "Set model for current provider")
        help_table.add_row("/model <provider> <name>", "Set model for a specific provider")
        help_table.add_row("/agentic on|off", "Enable or disable agentic decisions")
        help_table.add_row("/details on|off", "Show or hide full command details")
        help_table.add_row("/agentic-risk <low|medium>", "Max risk agentic mode can auto-execute")
        help_table.add_row("/compact on|off", "Toggle compact mode")
        help_table.add_row("/timestamps on|off", "Toggle message timestamps")
        help_table.add_row("/tips on|off", "Toggle chat tips")
        help_table.add_row("/preview <lines>", "Set command preview lines (3-30)")
        help_table.add_row("exit/quit", "Exit chat mode")
        
        self.console.print(help_table)
    
    def show_history(self, history_entries: List[Any]) -> None:
        """Show command history."""
        if not history_entries:
            self.console.print(f"[{self.profile.warning}]No history entries found[/]")
            return
        
        history_table = Table(title="Command History")
        history_table.add_column("Time", style=self.profile.secondary)
        history_table.add_column("Query", style="white")
        history_table.add_column("Command", style=self.profile.success)
        history_table.add_column("Status", style="white")
        
        for entry in history_entries[-10:]:  # Show last 10
            query = entry.get("query", "")
            command = entry.get("command", "")
            history_table.add_row(
                entry.get("timestamp", ""),
                query[:60] + "..." if len(query) > 60 else query,
                command[:60] + "..." if len(command) > 60 else command,
                "ok" if entry.get("success", False) else "failed",
            )
        
        self.console.print(history_table)
    
    def show_command_explanation(self, command: str, explanation: str) -> None:
        """Show command explanation."""
        self._refresh_preferences()
        syntax = Syntax(command, "bash", theme=self.profile.syntax_theme)
        command_panel = Panel(syntax, title="Command", border_style=self.profile.border)
        self.console.print(command_panel)
        
        explanation_panel = Panel(explanation, title="Explanation", border_style=self.profile.success)
        self.console.print(explanation_panel)

    def show_profile_summary(self) -> None:
        """Display current UI customization summary."""
        self._refresh_preferences()
        summary = Table(title="Terminal Customization")
        summary.add_column("Setting", style=self.profile.secondary)
        summary.add_column("Value", style="white")

        summary.add_row("Profile", self.profile.name)
        summary.add_row("Theme", str(self.config_manager.get_theme()))
        summary.add_row("Prompt style", str(self.ui_settings.get("prompt_style", "arrow")))
        summary.add_row("Compact mode", "on" if self.ui_settings.get("compact_mode", False) else "off")
        summary.add_row("Timestamps", "on" if self.ui_settings.get("show_timestamps", True) else "off")
        summary.add_row("Tips", "on" if self.ui_settings.get("show_tips", True) else "off")
        summary.add_row("Preview lines", str(self.ui_settings.get("command_preview_lines", 12)))
        summary.add_row(
            "Agentic mode",
            "on" if self.config_manager.get_bool("agentic_mode", False) else "off",
        )
        summary.add_row(
            "Show details",
            "on" if self.config_manager.get_bool("show_command_details", True) else "off",
        )
        summary.add_row(
            "Agentic max risk",
            self.config_manager.get_agentic_auto_execute_max_risk(),
        )
        self.console.print(summary)
