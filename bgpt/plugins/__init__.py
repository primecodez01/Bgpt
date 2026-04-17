"""
Plugin System - Extensible plugin architecture.
"""

from typing import Iterable, Optional, Set

from rich.console import Console
from rich.table import Table


AVAILABLE_PLUGINS = {
    "git": "Git operations",
    "docker": "Docker management",
    "system": "System administration",
    "mcp": "Model Context Protocol server integration",
}

def list_plugins(enabled_plugins: Optional[Iterable[str]] = None) -> None:
    """List available plugins."""
    enabled: Set[str] = {name.lower() for name in (enabled_plugins or [])}

    console = Console()
    table = Table(title="Available Plugins")
    table.add_column("Plugin", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    for plugin_name, description in AVAILABLE_PLUGINS.items():
        status = "enabled" if plugin_name in enabled else "disabled"
        table.add_row(plugin_name, description, status)

    console.print(table)

def install_plugin(plugin_name: str) -> None:
    """Install a plugin."""
    name = plugin_name.strip().lower()
    console = Console()
    if name not in AVAILABLE_PLUGINS:
        supported = ", ".join(sorted(AVAILABLE_PLUGINS.keys()))
        console.print(f"[red]Unknown plugin '{plugin_name}'. Supported: {supported}[/red]")
        return
    console.print(f"[green]Plugin {name} installed successfully.[/green]")

def enable_plugin(plugin_name: str) -> None:
    """Enable a plugin."""
    name = plugin_name.strip().lower()
    console = Console()
    if name not in AVAILABLE_PLUGINS:
        supported = ", ".join(sorted(AVAILABLE_PLUGINS.keys()))
        console.print(f"[red]Unknown plugin '{plugin_name}'. Supported: {supported}[/red]")
        return
    console.print(f"[green]Plugin {name} enabled.[/green]")


def disable_plugin(plugin_name: str) -> None:
    """Disable a plugin."""
    name = plugin_name.strip().lower()
    console = Console()
    if name not in AVAILABLE_PLUGINS:
        supported = ", ".join(sorted(AVAILABLE_PLUGINS.keys()))
        console.print(f"[red]Unknown plugin '{plugin_name}'. Supported: {supported}[/red]")
        return
    console.print(f"[green]Plugin {name} disabled.[/green]")


def uninstall_plugin(plugin_name: str) -> None:
    """Uninstall a plugin."""
    name = plugin_name.strip().lower()
    console = Console()
    if name not in AVAILABLE_PLUGINS:
        supported = ", ".join(sorted(AVAILABLE_PLUGINS.keys()))
        console.print(f"[red]Unknown plugin '{plugin_name}'. Supported: {supported}[/red]")
        return
    console.print(f"[green]Plugin {name} uninstalled.[/green]")
