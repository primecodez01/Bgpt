"""
Bgpt - Main CLI Application

This module provides the main CLI interface and application orchestration
for the Bgpt AI shell command assistant.
"""

import asyncio
import sys
from typing import List, Optional

import click
from rich.console import Console

from .core.ai_engine import AIEngine
from .core.command_parser import CommandParser
from .core.executor import CommandExecutor
from .core.safety import SafetyChecker
from .config.manager import ConfigManager
from .ui.terminal import TerminalUI
from .utils.logger import setup_logger
from .utils.history import HistoryManager


class BgptCLIGroup(click.Group):
    """Click group that allows free-form queries alongside subcommands."""

    def resolve_command(self, ctx: click.Context, args: List[str]):  # type: ignore[override]
        if not args:
            return None, None, args

        first = args[0]
        if first in self.commands:
            return super().resolve_command(ctx, args)

        if first.startswith("-"):
            return super().resolve_command(ctx, args)

        # Treat unknown first token as a natural-language query.
        query_command = self.get_command(ctx, "__query__")
        if query_command is None:
            return super().resolve_command(ctx, args)
        return "__query__", query_command, args


class Bgpt:
    """Main Bgpt application class."""

    def __init__(self) -> None:
        self.console = Console()
        self.config_manager = ConfigManager()
        self.logger = setup_logger()
        self.history_manager = HistoryManager()
        self.safety_checker = SafetyChecker()
        self.command_parser = CommandParser()
        self.executor = CommandExecutor(self.config_manager)
        self.ai_engine = AIEngine(self.config_manager)
        self.ui = TerminalUI(self.console, self.config_manager)

    def _recent_history_commands(self) -> List[str]:
        """Build short command history context for the AI engine."""
        return [
            entry.get("command", "")
            for entry in self.history_manager.get_recent(10)
            if entry.get("command")
        ]

    @staticmethod
    def _parse_on_off(value: str) -> Optional[bool]:
        """Parse on/off style user input into boolean."""
        normalized = value.strip().lower()
        if normalized in {"on", "true", "1", "yes", "y"}:
            return True
        if normalized in {"off", "false", "0", "no", "n"}:
            return False
        return None

    @staticmethod
    def _risk_rank(risk_level: str) -> int:
        """Map risk labels to sortable rank values."""
        return {"low": 1, "medium": 2, "high": 3}.get(risk_level.lower(), 3)

    def _handle_chat_command(self, query: str) -> bool:
        """Handle slash commands in chat mode. Returns True if handled."""
        if not query.startswith("/"):
            return False

        parts = query.strip().split()
        if not parts:
            return False

        command = parts[0].lower()
        args = parts[1:]

        try:
            if command == "/profile":
                if len(args) != 1:
                    self.ui.show_info("Usage: /profile <default|sunset|matrix|midnight|minimal>")
                    return True
                self.config_manager.set_terminal_profile(args[0])
                self.ui.show_success(f"Profile set to {self.config_manager.get_terminal_profile()}")
                self.ui.show_profile_summary()
                return True

            if command == "/style":
                if len(args) != 1:
                    self.ui.show_info("Usage: /style <arrow|classic|minimal>")
                    return True
                self.config_manager.set_ui_option("prompt_style", args[0])
                self.ui.show_success(f"Prompt style set to {args[0]}")
                return True

            if command == "/theme":
                if len(args) != 1:
                    self.ui.show_info("Usage: /theme <default|dark|light|hacker|minimal>")
                    return True
                self.config_manager.set_theme(args[0])
                self.ui.show_success(f"Theme set to {self.config_manager.get_theme()}")
                return True

            if command == "/compact":
                if len(args) != 1:
                    self.ui.show_info("Usage: /compact on|off")
                    return True
                enabled = self._parse_on_off(args[0])
                if enabled is None:
                    self.ui.show_error("Invalid value. Use on or off.")
                    return True
                self.config_manager.set_ui_option("compact_mode", enabled)
                self.ui.show_success(f"Compact mode {'enabled' if enabled else 'disabled'}")
                return True

            if command == "/timestamps":
                if len(args) != 1:
                    self.ui.show_info("Usage: /timestamps on|off")
                    return True
                enabled = self._parse_on_off(args[0])
                if enabled is None:
                    self.ui.show_error("Invalid value. Use on or off.")
                    return True
                self.config_manager.set_ui_option("show_timestamps", enabled)
                self.ui.show_success(f"Timestamps {'enabled' if enabled else 'disabled'}")
                return True

            if command == "/tips":
                if len(args) != 1:
                    self.ui.show_info("Usage: /tips on|off")
                    return True
                enabled = self._parse_on_off(args[0])
                if enabled is None:
                    self.ui.show_error("Invalid value. Use on or off.")
                    return True
                self.config_manager.set_ui_option("show_tips", enabled)
                self.ui.show_success(f"Tips {'enabled' if enabled else 'disabled'}")
                return True

            if command == "/preview":
                if len(args) != 1:
                    self.ui.show_info("Usage: /preview <3-30>")
                    return True
                preview_lines = int(args[0])
                self.config_manager.set_ui_option("command_preview_lines", preview_lines)
                self.ui.show_success(f"Command preview lines set to {preview_lines}")
                return True

            if command == "/provider":
                if len(args) != 1:
                    self.ui.show_info("Usage: /provider <gemini|openai|anthropic|local>")
                    return True
                self.config_manager.set_provider(args[0])
                active_provider = self.config_manager.get_provider()
                active_model = self.config_manager.get_provider_model(active_provider)
                self.ui.show_success(f"Provider set to {active_provider} (model: {active_model})")
                return True

            if command == "/model":
                if len(args) == 1:
                    target_provider = self.config_manager.get_provider()
                    model_name = args[0]
                elif len(args) >= 2:
                    target_provider = args[0]
                    model_name = " ".join(args[1:])
                else:
                    self.ui.show_info("Usage: /model <name> or /model <provider> <name>")
                    return True

                self.config_manager.set_provider_model(target_provider, model_name)
                normalized_provider = self.config_manager.normalize_provider(target_provider) or target_provider
                active_model = self.config_manager.get_provider_model(normalized_provider)
                self.ui.show_success(f"Model set for {normalized_provider}: {active_model}")
                return True

            if command == "/safety":
                if len(args) != 1:
                    self.ui.show_info("Usage: /safety <low|medium|high>")
                    return True
                self.config_manager.set_safety_level(args[0])
                self.ui.show_success(f"Safety level set to {self.config_manager.get_safety_level()}")
                return True

            if command == "/timeout":
                if len(args) != 1:
                    self.ui.show_info("Usage: /timeout <seconds>")
                    return True
                timeout_seconds = int(args[0])
                self.config_manager.set_command_timeout(timeout_seconds)
                self.ui.show_success(
                    f"Command timeout set to {self.config_manager.get_command_timeout()} seconds"
                )
                return True

            if command == "/agentic":
                if len(args) != 1:
                    self.ui.show_info("Usage: /agentic on|off")
                    return True
                enabled = self._parse_on_off(args[0])
                if enabled is None:
                    self.ui.show_error("Invalid value. Use on or off.")
                    return True
                self.config_manager.set_bool("agentic_mode", enabled)
                self.ui.show_success(f"Agentic mode {'enabled' if enabled else 'disabled'}")
                return True

            if command == "/details":
                if len(args) != 1:
                    self.ui.show_info("Usage: /details on|off")
                    return True
                enabled = self._parse_on_off(args[0])
                if enabled is None:
                    self.ui.show_error("Invalid value. Use on or off.")
                    return True
                self.config_manager.set_bool("show_command_details", enabled)
                self.ui.show_success(
                    f"Command detail display {'enabled' if enabled else 'disabled'}"
                )
                return True

            if command == "/agentic-risk":
                if len(args) != 1:
                    self.ui.show_info("Usage: /agentic-risk <low|medium>")
                    return True
                self.config_manager.set_agentic_auto_execute_max_risk(args[0])
                self.ui.show_success(
                    "Agentic max auto-execution risk set to: "
                    f"{self.config_manager.get_agentic_auto_execute_max_risk()}"
                )
                return True

            if command == "/config":
                self.ui.show_profile_summary()
                return True

            self.ui.show_warning("Unknown slash command. Type 'help' to view commands.")
            return True
        except ValueError as error:
            self.ui.show_error(str(error))
            return True
        except Exception as error:
            self.ui.show_error(f"Failed to apply setting: {error}")
            return True

    async def process_query(self, query: str, interactive: bool = False) -> bool:
        """Process a user query and generate/execute commands."""
        try:
            active_provider = self.config_manager.get_provider()
            try:
                active_model = self.config_manager.get_provider_model(active_provider)
            except ValueError:
                active_model = "default"

            # Generate command using AI
            with self.ui.thinking(f"Generating command ({active_provider}:{active_model})"):
                command_result = await self.ai_engine.generate_command(
                    query,
                    recent_history=self._recent_history_commands(),
                )

            if not command_result:
                self.ui.show_error("Failed to generate command")
                return False

            is_valid, syntax_errors = self.command_parser.validate_syntax(command_result.command)
            if not is_valid:
                for syntax_error in syntax_errors:
                    self.ui.show_warning(syntax_error)
                self.ui.show_error("Generated command failed syntax validation")
                return False

            # Parse and validate command
            parsed_command = self.command_parser.parse(command_result.command)

            # Safety check
            safety_result = self.safety_checker.check_command(
                parsed_command,
                command_result.safety_level,
            )

            show_command_details = self.config_manager.get_bool("show_command_details", True)
            agentic_mode = self.config_manager.get_bool("agentic_mode", False)

            # Display command with safety info (optional in agentic mode)
            if show_command_details or not agentic_mode:
                self.ui.display_command_result(command_result, safety_result)
            else:
                self.ui.show_info(
                    "Agentic summary: "
                    f"provider={command_result.provider_used}, "
                    f"risk={getattr(safety_result.risk_level, 'value', 'unknown')}"
                )

            if not safety_result.allow_execution:
                self.ui.show_warning("Command blocked by safety checker")
                return False

            auto_execute = self.config_manager.get_bool("auto_execute", False)
            if agentic_mode:
                max_auto_risk = self.config_manager.get_agentic_auto_execute_max_risk()
                command_risk = str(getattr(safety_result.risk_level, "value", "high"))
                within_auto_risk = self._risk_rank(command_risk) <= self._risk_rank(max_auto_risk)
                can_agent_auto_execute = (
                    auto_execute
                    and within_auto_risk
                    and not parsed_command.uses_sudo
                )
                should_confirm = not can_agent_auto_execute
                if not show_command_details:
                    if can_agent_auto_execute:
                        self.ui.show_info("Agentic mode: auto-executing this command.")
                    else:
                        self.ui.show_info("Agentic mode: confirmation required for this command.")
            else:
                should_confirm = safety_result.requires_confirmation or (interactive and not auto_execute)

            if should_confirm and not self.ui.confirm_execution(
                command_result,
                safety_result,
                force=(interactive and not auto_execute),
            ):
                self.ui.show_info("Command execution cancelled")
                return False

            # Execute command
            with self.ui.thinking("Executing command"):
                execution_result = await self.executor.execute(
                    parsed_command,
                    safety_result.sandbox,
                )

            # Display results
            self.ui.display_execution_result(execution_result)

            # Save to history
            if self.config_manager.get_bool("save_history", True):
                # Save to history
                self.history_manager.add_entry(query, command_result, execution_result)

            return execution_result.success

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            self.ui.show_error(f"Error: {e}")
            return False

    async def chat_mode(self) -> None:
        """Interactive chat mode."""
        self.ui.show_welcome()
        self.ui.show_chat_header()

        while True:
            try:
                query = self.ui.get_chat_input()

                if not query.strip():
                    continue

                if query.lower() in ['exit', 'quit', 'bye']:
                    self.ui.show_goodbye()
                    break

                if query.lower() == 'help':
                    self.ui.show_help()
                    continue

                if query.lower() == 'history':
                    self.ui.show_history(self.history_manager.get_recent())
                    continue

                if self._handle_chat_command(query):
                    continue

                await self.process_query(query, interactive=True)

            except KeyboardInterrupt:
                self.ui.show_goodbye()
                break
            except EOFError:
                break

    def tui_mode(self) -> None:
        """Launch the textual TUI interface."""
        try:
            from .ui.tui_app import BgptTUIApp
            app = BgptTUIApp(self)
            app.run()
        except ImportError:
            self.ui.show_error("TUI mode not available. Please install textual>=0.50.0")
            self.ui.show_info("Falling back to chat mode...")
            asyncio.run(self.chat_mode())


@click.group(
    cls=BgptCLIGroup,
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.option('--chat', is_flag=True, help='Start interactive chat mode')
@click.option('--tui', is_flag=True, help='Launch TUI interface')
@click.option('--explain', metavar='COMMAND', help='Explain an existing command')
@click.option('--history', is_flag=True, help='Show command history')
@click.option('--setup', is_flag=True, help='Run setup wizard')
@click.option('--doctor', is_flag=True, help='Run system diagnostics')
@click.option('--version', is_flag=True, help='Show version information')
@click.pass_context
def cli(ctx: click.Context, chat: bool, tui: bool,
    explain: Optional[str], history: bool, setup: bool, doctor: bool,
        version: bool) -> None:
    """Bgpt - Advanced AI Shell Command Assistant
    
    Transform natural language into powerful shell commands with AI.
    
    Examples:
        bgpt "find all python files larger than 1MB"
        bgpt --chat
        bgpt --explain "ls -la"
        bgpt --setup
    """
    if version:
        from . import __version__
        click.echo(f"Bgpt version {__version__}")
        return

    app = Bgpt()

    if setup:
        app.config_manager.run_setup_wizard()
        return

    if doctor:
        app.config_manager.run_diagnostics()
        return

    if explain:
        asyncio.run(app.ai_engine.explain_command(explain))
        return

    if history:
        app.ui.show_history(app.history_manager.get_recent())
        return

    if tui:
        app.tui_mode()
        return

    if chat:
        asyncio.run(app.chat_mode())
        return

    query = " ".join(ctx.args).strip()
    if query:
        success = asyncio.run(app.process_query(query, interactive=True))
        sys.exit(0 if success else 1)
    else:
        # No arguments - show help or start chat
        if ctx.invoked_subcommand is None:
            asyncio.run(app.chat_mode())


@cli.command(name="__query__", hidden=True)
@click.argument("query_tokens", nargs=-1, required=True)
def query_command(query_tokens: List[str]) -> None:
    """Internal command used to route free-form one-shot queries."""
    app = Bgpt()
    query = " ".join(query_tokens).strip()
    success = asyncio.run(app.process_query(query, interactive=True))
    sys.exit(0 if success else 1)


@cli.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command()
@click.option('--provider', type=click.Choice([
    'gemini', 'openai', 'anthropic', 'local', 'gpt4', 'gpt3.5', 'claude', 'ollama'
]))
@click.option('--theme', type=click.Choice(['default', 'dark', 'light', 'hacker', 'minimal']))
@click.option('--safety-level', type=click.Choice(['low', 'medium', 'high']))
@click.option('--profile', type=click.Choice(['default', 'sunset', 'matrix', 'midnight', 'minimal']))
@click.option('--prompt-style', type=click.Choice(['arrow', 'classic', 'minimal']))
@click.option('--compact/--no-compact', default=None)
@click.option('--timestamps/--no-timestamps', default=None)
@click.option('--tips/--no-tips', default=None)
@click.option('--preview-lines', type=click.IntRange(3, 30))
@click.option('--timeout', type=click.IntRange(5, 600))
@click.option('--auto-execute/--no-auto-execute', default=None)
@click.option('--save-history/--no-save-history', default=None)
@click.option('--agentic/--no-agentic', default=None)
@click.option('--show-details/--hide-details', default=None)
@click.option('--agentic-risk', type=click.Choice(['low', 'medium']))
@click.option('--model', help='Model id to use for a provider')
@click.option('--model-provider', type=click.Choice(['gemini', 'openai', 'anthropic', 'local']))
def set(
    provider: Optional[str],
    theme: Optional[str],
    safety_level: Optional[str],
    profile: Optional[str],
    prompt_style: Optional[str],
    compact: Optional[bool],
    timestamps: Optional[bool],
    tips: Optional[bool],
    preview_lines: Optional[int],
    timeout: Optional[int],
    auto_execute: Optional[bool],
    save_history: Optional[bool],
    agentic: Optional[bool],
    show_details: Optional[bool],
    agentic_risk: Optional[str],
    model: Optional[str],
    model_provider: Optional[str],
) -> None:
    """Set configuration options."""
    config_manager = ConfigManager()

    if provider:
        config_manager.set_provider(provider)
        click.echo(f"Provider set to: {config_manager.get_provider()}")

    if theme:
        config_manager.set_theme(theme)
        click.echo(f"Theme set to: {theme}")

    if safety_level:
        config_manager.set_safety_level(safety_level)
        click.echo(f"Safety level set to: {safety_level}")

    if profile:
        config_manager.set_terminal_profile(profile)
        click.echo(f"Profile set to: {profile}")

    if prompt_style:
        config_manager.set_ui_option("prompt_style", prompt_style)
        click.echo(f"Prompt style set to: {prompt_style}")

    if compact is not None:
        config_manager.set_ui_option("compact_mode", compact)
        click.echo(f"Compact mode {'enabled' if compact else 'disabled'}")

    if timestamps is not None:
        config_manager.set_ui_option("show_timestamps", timestamps)
        click.echo(f"Timestamps {'enabled' if timestamps else 'disabled'}")

    if tips is not None:
        config_manager.set_ui_option("show_tips", tips)
        click.echo(f"Tips {'enabled' if tips else 'disabled'}")

    if preview_lines is not None:
        config_manager.set_ui_option("command_preview_lines", preview_lines)
        click.echo(f"Command preview lines set to: {preview_lines}")

    if timeout is not None:
        config_manager.set_command_timeout(timeout)
        click.echo(f"Command timeout set to: {timeout} seconds")

    if auto_execute is not None:
        config_manager.set_bool("auto_execute", auto_execute)
        click.echo(f"Auto execute {'enabled' if auto_execute else 'disabled'}")

    if save_history is not None:
        config_manager.set_bool("save_history", save_history)
        click.echo(f"History saving {'enabled' if save_history else 'disabled'}")

    if agentic is not None:
        config_manager.set_bool("agentic_mode", agentic)
        click.echo(f"Agentic mode {'enabled' if agentic else 'disabled'}")

    if show_details is not None:
        config_manager.set_bool("show_command_details", show_details)
        click.echo(f"Command details {'enabled' if show_details else 'hidden'}")

    if agentic_risk:
        config_manager.set_agentic_auto_execute_max_risk(agentic_risk)
        click.echo(f"Agentic auto-execution max risk set to: {agentic_risk}")

    if model:
        if model_provider:
            target_provider = model_provider
        elif provider:
            target_provider = provider
        else:
            target_provider = config_manager.get_provider()

        config_manager.set_provider_model(target_provider, model)
        normalized_provider = config_manager.normalize_provider(target_provider) or target_provider
        click.echo(f"Model for {normalized_provider} set to: {config_manager.get_provider_model(normalized_provider)}")


@config.command()
def show() -> None:
    """Show current configuration."""
    config_manager = ConfigManager()
    config_manager.show_config()


@cli.group()
def plugins() -> None:
    """Plugin management commands."""
    pass


@plugins.command()
def list() -> None:
    """List available plugins."""
    from .plugins import list_plugins
    config_manager = ConfigManager()
    list_plugins(config_manager.get_enabled_plugins())


@plugins.command()
@click.argument('plugin_name')
def install(plugin_name: str) -> None:
    """Install a plugin."""
    from .plugins import install_plugin
    install_plugin(plugin_name)


@plugins.command()
@click.argument('plugin_name')
def uninstall(plugin_name: str) -> None:
    """Uninstall a plugin."""
    from .plugins import uninstall_plugin

    config_manager = ConfigManager()
    config_manager.disable_plugin(plugin_name)
    uninstall_plugin(plugin_name)


@plugins.command()
@click.argument('plugin_name')
def enable(plugin_name: str) -> None:
    """Enable a plugin."""
    from .plugins import enable_plugin
    config_manager = ConfigManager()
    config_manager.enable_plugin(plugin_name)
    enable_plugin(plugin_name)


@plugins.command()
@click.argument('plugin_name')
def disable(plugin_name: str) -> None:
    """Disable a plugin."""
    from .plugins import disable_plugin

    config_manager = ConfigManager()
    config_manager.disable_plugin(plugin_name)
    disable_plugin(plugin_name)


@cli.command('setup-local')
def setup_local_command() -> None:
    """Setup local AI models for offline use."""
    from bgpt.setup_local import main as setup_main
    setup_main()


def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nGoodbye!")
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
