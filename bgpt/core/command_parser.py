"""
Command Parser - Parse and validate shell commands.

This module provides functionality to parse shell commands, extract
components, and validate syntax.
"""

import re
import shlex
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedCommand:
    """Parsed shell command structure."""
    raw_command: str
    base_command: str
    arguments: List[str]
    flags: List[str]
    redirections: List[Tuple[str, str]]  # (type, target)
    pipes: List[str]
    environment_vars: Dict[str, str]
    background: bool
    uses_sudo: bool
    file_operations: List[str]
    network_operations: List[str]
    system_operations: List[str]


class CommandParser:
    """Shell command parser and analyzer."""
    
    # Dangerous command patterns
    DESTRUCTIVE_PATTERNS = {
        r'rm\s+-rf\s+/': 'Recursive deletion of root directory',
        r'dd\s+.*of=/dev/': 'Direct disk writing operation',
        r'mkfs\.*': 'File system formatting',
        r'fdisk.*': 'Disk partitioning',
        r'format\s+': 'Drive formatting',
        r':\(\)\{.*\}': 'Fork bomb pattern',
        r'chmod\s+777': 'Overly permissive permissions',
        r'chown\s+.*:\s*/': 'Root ownership change',
    }
    
    # Network operation patterns
    NETWORK_PATTERNS = {
        r'\bcurl\b': 'curl',
        r'\bwget\b': 'wget',
        r'\bssh\b': 'ssh',
        r'\bscp\b': 'scp',
        r'\brsync\b': 'rsync',
        r'\bnc\b': 'nc',
        r'\bnetcat\b': 'netcat',
        r'\btelnet\b': 'telnet',
        r'\bftp\b': 'ftp',
        r'\bsftp\b': 'sftp',
    }
    
    # System modification patterns
    SYSTEM_PATTERNS = {
        r'\bsystemctl\b': 'systemctl',
        r'\bservice\b': 'service',
        r'\bmount\b': 'mount',
        r'\bumount\b': 'umount',
        r'\bmodprobe\b': 'modprobe',
        r'\binsmod\b': 'insmod',
        r'\brmmod\b': 'rmmod',
        r'\biptables\b': 'iptables',
    }
    
    # File operation patterns
    FILE_PATTERNS = {
        r'\bcp\b': 'cp',
        r'\bmv\b': 'mv',
        r'\brm\b': 'rm',
        r'\bmkdir\b': 'mkdir',
        r'\brmdir\b': 'rmdir',
        r'\btouch\b': 'touch',
        r'\bln\b': 'ln',
        r'\btar\b': 'tar',
        r'\bzip\b': 'zip',
        r'\bunzip\b': 'unzip',
    }
    
    def __init__(self) -> None:
        self.logger = logger
        
    def parse(self, command: str) -> ParsedCommand:
        """Parse a shell command into its components."""
        original_command = command.strip()

        try:
            # Check for background execution
            background = bool(re.search(r'\s*&\s*$', original_command))
            working_command = re.sub(r'\s*&\s*$', '', original_command).strip()

            # Tokenize for structured parsing
            tokens = shlex.split(working_command)
            if not tokens:
                raise ValueError("Empty command")

            # Extract leading environment variable assignments
            env_vars: Dict[str, str] = {}
            token_index = 0
            while token_index < len(tokens):
                token = tokens[token_index]
                if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=.*$', token):
                    key, value = token.split('=', 1)
                    env_vars[key] = value
                    token_index += 1
                    continue
                break

            command_tokens = tokens[token_index:]
            if not command_tokens:
                raise ValueError("Missing command after environment variable assignment")

            uses_sudo = command_tokens[0] == 'sudo'
            if uses_sudo:
                command_tokens = command_tokens[1:]
            if not command_tokens:
                raise ValueError("Missing command after sudo")

            # Parse command components
            base_command = command_tokens[0]
            arguments: List[str] = []
            flags: List[str] = []

            for part in command_tokens[1:]:
                if part.startswith('-'):
                    flags.append(part)
                else:
                    arguments.append(part)

            # Extract pipes/redirections from working command
            pipes = self._extract_pipes(working_command)
            redirections = self._extract_redirections(working_command)

            # Analyze command categories
            file_ops = self._analyze_file_operations(working_command)
            network_ops = self._analyze_network_operations(working_command)
            system_ops = self._analyze_system_operations(working_command)

            if background:
                raw_command = f"{working_command} &"
            else:
                raw_command = working_command

            return ParsedCommand(
                raw_command=raw_command,
                base_command=base_command,
                arguments=arguments,
                flags=flags,
                redirections=redirections,
                pipes=pipes,
                environment_vars=env_vars,
                background=background,
                uses_sudo=uses_sudo,
                file_operations=file_ops,
                network_operations=network_ops,
                system_operations=system_ops
            )

        except Exception as e:
            self.logger.error(f"Failed to parse command '{original_command}': {e}")
            # Return minimal parsed command
            return ParsedCommand(
                raw_command=original_command,
                base_command=original_command.split()[0] if original_command.split() else '',
                arguments=[],
                flags=[],
                redirections=[],
                pipes=[],
                environment_vars={},
                background=False,
                uses_sudo=original_command.startswith('sudo '),
                file_operations=[],
                network_operations=[],
                system_operations=[]
            )
    
    def _extract_env_vars(self, command: str) -> Dict[str, str]:
        """Extract environment variable assignments."""
        env_vars = {}
        parts = command.split()
        
        for part in parts:
            if '=' in part and not part.startswith('-'):
                key, value = part.split('=', 1)
                if key.isidentifier():
                    env_vars[key] = value
                    
        return env_vars
    
    def _extract_pipes(self, command: str) -> List[str]:
        """Extract pipe operations."""
        if '|' in command:
            # Ignore logical OR operator (||) when splitting pipelines.
            parts = [part.strip() for part in re.split(r'(?<!\|)\|(?!\|)', command)]
            return parts[1:] if len(parts) > 1 else []
        return []
    
    def _extract_redirections(self, command: str) -> List[Tuple[str, str]]:
        """Extract redirection operations."""
        redirections = []

        # Output redirections (ordered from most specific to least specific).
        for match in re.finditer(r'(?P<op>\d?>>|>>|\d?>|>)\s*(?P<target>\S+)', command):
            redirections.append((match.group('op'), match.group('target')))

        # Input redirections
        for match in re.finditer(r'(?P<op><<|<)\s*(?P<target>\S+)', command):
            redirections.append((match.group('op'), match.group('target')))

        return redirections
    
    def _analyze_file_operations(self, command: str) -> List[str]:
        """Analyze file operations in command."""
        operations = []
        for pattern, operation_name in self.FILE_PATTERNS.items():
            if re.search(pattern, command, re.IGNORECASE):
                operations.append(operation_name)
        return operations
    
    def _analyze_network_operations(self, command: str) -> List[str]:
        """Analyze network operations in command."""
        operations = []
        for pattern, operation_name in self.NETWORK_PATTERNS.items():
            if re.search(pattern, command, re.IGNORECASE):
                operations.append(operation_name)
        return operations
    
    def _analyze_system_operations(self, command: str) -> List[str]:
        """Analyze system operations in command."""
        operations = []
        for pattern, operation_name in self.SYSTEM_PATTERNS.items():
            if re.search(pattern, command, re.IGNORECASE):
                operations.append(operation_name)
        return operations
    
    def is_destructive(self, command: str) -> Tuple[bool, List[str]]:
        """Check if command contains destructive patterns."""
        warnings = []
        
        for pattern, description in self.DESTRUCTIVE_PATTERNS.items():
            if re.search(pattern, command, re.IGNORECASE):
                warnings.append(description)
        
        return len(warnings) > 0, warnings
    
    def validate_syntax(self, command: str) -> Tuple[bool, List[str]]:
        """Validate command syntax."""
        errors = []
        
        try:
            # Try to parse with shlex
            shlex.split(command)
        except ValueError as e:
            errors.append(f"Shell syntax error: {e}")
        
        # Check for unmatched quotes
        if command.count('"') % 2 != 0:
            errors.append("Unmatched double quotes")
        if command.count("'") % 2 != 0:
            errors.append("Unmatched single quotes")
        
        # Check for dangerous combinations
        if (
            re.search(r'\brm\b', command)
            and re.search(r'\-[^\s]*r[^\s]*f|\-[^\s]*f[^\s]*r', command)
            and ("*" in command or re.search(r'\s/($|\s|\w)', command))
        ):
            errors.append("Potentially dangerous rm command with recursive force flags")
        
        return len(errors) == 0, errors
    
    def get_command_info(self, parsed_command: ParsedCommand) -> Dict[str, Any]:
        """Get comprehensive information about a parsed command."""
        return {
            'base_command': parsed_command.base_command,
            'argument_count': len(parsed_command.arguments),
            'flag_count': len(parsed_command.flags),
            'has_pipes': len(parsed_command.pipes) > 0,
            'has_redirections': len(parsed_command.redirections) > 0,
            'uses_sudo': parsed_command.uses_sudo,
            'runs_background': parsed_command.background,
            'file_operations': parsed_command.file_operations,
            'network_operations': parsed_command.network_operations,
            'system_operations': parsed_command.system_operations,
            'complexity_score': self._calculate_complexity(parsed_command)
        }
    
    def _calculate_complexity(self, parsed_command: ParsedCommand) -> int:
        """Calculate command complexity score (0-10)."""
        score = 0
        
        # Base complexity
        score += min(len(parsed_command.arguments), 3)
        score += min(len(parsed_command.flags), 3)
        
        # Additional complexity factors
        if parsed_command.pipes:
            score += 2
        if parsed_command.redirections:
            score += 1
        if parsed_command.uses_sudo:
            score += 1
        if parsed_command.file_operations:
            score += 1
        if parsed_command.network_operations:
            score += 2
        if parsed_command.system_operations:
            score += 2
            
        return min(score, 10)
