"""
Safety Checker - Security and safety validation for commands.

This module provides comprehensive safety checking for shell commands
to prevent dangerous operations.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple

from .ai_engine import SafetyLevel
from .command_parser import ParsedCommand
from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class SafetyResult:
    """Result of safety checking."""

    allow_execution: bool
    risk_level: SafetyLevel
    warnings: List[str]
    sandbox: bool
    requires_confirmation: bool
    risk_score: int

class SafetyChecker:
    """Command safety validation system."""

    BLOCKED_PATTERNS: List[Tuple[str, str]] = [
        (r"\brm\s+-rf\s+/(\s|$)", "Recursive deletion of root filesystem"),
        (r"\bmkfs(\.|\b)", "Filesystem formatting command"),
        (r"\bdd\s+.*\bof=/dev/(sd|nvme|vd)", "Direct write to block device"),
        (r"\b: *\( *\) *\{ *: *\| *: *& *\} *; *:", "Fork bomb pattern"),
        (r"\bshutdown\b\s+(-h|--halt|now)", "System shutdown command"),
    ]

    HIGH_RISK_PATTERNS: List[Tuple[str, str]] = [
        (r"\brm\s+-rf\b", "Recursive deletion can remove large directory trees"),
        (r"\bchmod\s+777\b", "Overly permissive file permissions"),
        (r">\s*/dev/", "Redirecting output to device files"),
        (r"\b(usermod|groupmod|passwd)\b", "User or group account modification"),
        (r"\bsystemctl\s+(stop|disable|mask)\b", "Service disabling operation"),
    ]

    MEDIUM_RISK_PATTERNS: List[Tuple[str, str]] = [
        (r"\bcurl\b.*\|\s*(bash|sh)\b", "Remote script execution through shell pipeline"),
        (r"\bchown\b", "Ownership change operation"),
        (r"\biptables\b", "Firewall rule changes"),
        (r"\bmount\b|\bumount\b", "Filesystem mount changes"),
    ]

    def check_command(self, parsed_command: ParsedCommand, ai_safety_level: SafetyLevel) -> SafetyResult:
        """Check command safety."""
        command_text = parsed_command.raw_command.strip()
        warnings: List[str] = []
        allow_execution = True
        sandbox = False
        requires_confirmation = False

        risk_score = 0

        # Check for blocked commands (hard fail)
        for pattern, reason in self.BLOCKED_PATTERNS:
            if re.search(pattern, command_text, re.IGNORECASE):
                warnings.append(f"Blocked: {reason}")
                allow_execution = False

        # Static risk heuristics
        if parsed_command.uses_sudo:
            warnings.append("Command requires sudo privileges")
            risk_score += 2

        if parsed_command.file_operations:
            warnings.append("Command performs file operations")
            risk_score += 1

        if parsed_command.network_operations:
            warnings.append("Command performs network operations")
            risk_score += 1
            sandbox = True

        if parsed_command.system_operations:
            warnings.append("Command changes system state")
            risk_score += 2

        if parsed_command.pipes:
            risk_score += 1

        if parsed_command.redirections:
            risk_score += 1

        for pattern, reason in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, command_text, re.IGNORECASE):
                warnings.append(f"High risk: {reason}")
                risk_score += 3

        for pattern, reason in self.MEDIUM_RISK_PATTERNS:
            if re.search(pattern, command_text, re.IGNORECASE):
                warnings.append(f"Caution: {reason}")
                risk_score += 2

        ai_risk_bonus = {
            SafetyLevel.LOW: 0,
            SafetyLevel.MEDIUM: 1,
            SafetyLevel.HIGH: 3,
        }.get(ai_safety_level, 1)
        risk_score += ai_risk_bonus

        if risk_score >= 7:
            risk_level = SafetyLevel.HIGH
        elif risk_score >= 4:
            risk_level = SafetyLevel.MEDIUM
        else:
            risk_level = SafetyLevel.LOW

        if risk_level == SafetyLevel.HIGH:
            sandbox = True

        requires_confirmation = (
            not allow_execution
            or risk_level != SafetyLevel.LOW
            or parsed_command.uses_sudo
            or ai_safety_level != SafetyLevel.LOW
        )

        if allow_execution and risk_level == SafetyLevel.HIGH:
            warnings.append("Execution is high-risk. Review the command before running.")

        return SafetyResult(
            allow_execution=allow_execution,
            risk_level=risk_level,
            warnings=warnings,
            sandbox=sandbox,
            requires_confirmation=requires_confirmation,
            risk_score=min(risk_score, 10),
        )
