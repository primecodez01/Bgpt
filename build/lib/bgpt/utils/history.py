"""
History Manager - Command history management.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

class HistoryManager:
    """Command history management."""

    def __init__(self) -> None:
        self.history_file = Path.home() / ".bgpt" / "history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load history from file."""
        if self.history_file.exists():
            try:
                with self.history_file.open("r", encoding="utf-8") as history_handle:
                    loaded = json.load(history_handle)
                    if isinstance(loaded, list):
                        return [entry for entry in loaded if isinstance(entry, dict)]
            except Exception:
                return []
        return []

    def _save_history(self) -> None:
        """Save history to file."""
        temp_file = self.history_file.with_suffix(".tmp")
        with temp_file.open("w", encoding="utf-8") as history_handle:
            json.dump(self.history, history_handle, indent=2)
        temp_file.replace(self.history_file)

    def add_entry(self, query: str, command_result: Any, execution_result: Any) -> None:
        """Add new history entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "command": command_result.command,
            "explanation": command_result.explanation,
            "success": execution_result.success,
            "return_code": execution_result.return_code,
            "execution_time": execution_result.execution_time,
            "provider": command_result.provider_used
        }
        self.history.append(entry)

        # Keep only last 1000 entries
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

        self._save_history()

    def get_recent(self, count: int = 20) -> List[Dict[str, Any]]:
        """Get recent history entries."""
        if count <= 0:
            return []
        return self.history[-count:]

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search history entries."""
        results = []
        query_lower = query.lower()
        for entry in self.history:
            if (query_lower in entry["query"].lower() or 
                query_lower in entry["command"].lower()):
                results.append(entry)
        return results
