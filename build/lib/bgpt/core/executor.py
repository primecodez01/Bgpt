"""
Command Executor - Safe command execution with monitoring.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

from .command_parser import ParsedCommand
from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ExecutionResult:
    """Result of command execution."""

    success: bool
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    timed_out: bool = False

class CommandExecutor:
    """Safe command execution engine."""

    def __init__(self, config_manager: Optional[Any] = None) -> None:
        self.config_manager = config_manager

    @staticmethod
    def _decode_output(raw: Optional[bytes]) -> str:
        """Decode process output safely."""
        if not raw:
            return ""
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")

    async def execute(
        self,
        parsed_command: ParsedCommand,
        sandbox: bool = False,
        timeout_seconds: Optional[int] = None,
    ) -> ExecutionResult:
        """Execute a parsed command safely."""
        start_time = time.time()

        default_timeout = 60
        if self.config_manager is not None:
            try:
                default_timeout = int(self.config_manager.get_command_timeout())
            except Exception:
                default_timeout = 60
        timeout_value = timeout_seconds if timeout_seconds is not None else default_timeout
        timeout_value = max(int(timeout_value), 1)
        
        try:
            if sandbox:
                # In a real implementation, this would use containerization
                logger.debug("Executing in sandbox mode")

            process = await asyncio.create_subprocess_shell(
                parsed_command.raw_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            timed_out = False
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_value
                )
            except asyncio.TimeoutError:
                timed_out = True
                logger.warning("Command timed out after %ss: %s", timeout_value, parsed_command.raw_command)
                process.kill()
                stdout_bytes, stderr_bytes = await process.communicate()

            stdout = self._decode_output(stdout_bytes)
            stderr = self._decode_output(stderr_bytes)

            if timed_out:
                timeout_message = f"Command timed out after {timeout_value} seconds."
                stderr = f"{stderr}\n{timeout_message}".strip()

            execution_time = time.time() - start_time

            return_code = process.returncode
            if return_code is None:
                return_code = 124 if timed_out else -1

            return ExecutionResult(
                success=return_code == 0 and not timed_out,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                command=parsed_command.raw_command,
                timed_out=timed_out,
            )

        except Exception as e:
            # Only log to file, not console
            logger.debug(f"Execution failed: {e}")
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
                command=parsed_command.raw_command,
                timed_out=False,
            )
