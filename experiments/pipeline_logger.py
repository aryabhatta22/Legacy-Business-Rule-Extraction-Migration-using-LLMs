"""Unified logging for console and file output.

This module handles:
1. Logging to console (with hierarchy indentation)
2. Logging to file (experiments/run_log.txt)
3. Separate logs from experiment results
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict


class PipelineLogger:
    """Unified logger for console and file output."""

    def __init__(self, log_file: str = "experiments/run_log.txt"):
        """Initialize logger.

        Args:
            log_file: Path to write logs
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Write header
        self._write_header()

    def _write_header(self):
        """Write log file header."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("COBOL Converter Experiment Log\n")
            f.write(f"Started: {datetime.utcnow().isoformat()}Z\n")
            f.write("=" * 60 + "\n\n")

    def log(self, message: str, level: str = "INFO", indent: int = 0):
        """Log a message to both console and file.

        Args:
            message: Message text
            level: Log level (INFO, WARN, ERROR, DEBUG)
            indent: Indentation level (0, 1, 2, etc.)
        """
        # Format message with indentation and timestamp
        indent_str = "  " * indent
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"{indent_str}[{timestamp}] {level}: {message}"

        # Print to console
        print(formatted)
        sys.stdout.flush()

        # Write to file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except IOError as e:
            print(f"[ERROR] Failed to write to log file: {e}")

    def pipeline_start(self):
        """Log pipeline start."""
        self.log("PIPELINE STARTING", level="INFO", indent=0)

    def pipeline_end(self):
        """Log pipeline end."""
        self.log("PIPELINE COMPLETE", level="INFO", indent=0)

    def program_start(self, program_name: str):
        """Log program processing start."""
        self.log(f"Processing program: {program_name}", level="INFO", indent=0)

    def task_start(self, task: str, strategy: str):
        """Log task start."""
        self.log(f"Task: {task} | Strategy: {strategy}", level="INFO", indent=1)

    def model_start(self, model_name: str):
        """Log model start."""
        self.log(f"Model: {model_name}", level="INFO", indent=2)

    def llm_call_start(self):
        """Log LLM call start."""
        self.log("Calling LLM...", level="INFO", indent=3)

    def json_extraction(self, success: bool):
        """Log JSON extraction result."""
        status = "SUCCESS" if success else "FAILED"
        self.log(f"JSON extraction: {status}", level="INFO", indent=3)

    def schema_validation(self, success: bool, reason: Optional[str] = None):
        """Log schema validation result."""
        status = "VALID" if success else "INVALID"
        msg = f"Schema validation: {status}"
        if reason:
            msg += f" ({reason})"
        self.log(msg, level="INFO", indent=3)

    def evaluation_complete(self, metrics: Dict[str, int]):
        """Log evaluation completion."""
        msg = (
            f"Evaluation complete - "
            f"correct={metrics.get('correct', 0)} "
            f"partial={metrics.get('partial', 0)} "
            f"missing={metrics.get('missing', 0)} "
            f"hallucinated={metrics.get('hallucinated', 0)}"
        )
        self.log(msg, level="INFO", indent=3)

    def error(self, message: str, indent: int = 3):
        """Log error message."""
        self.log(message, level="ERROR", indent=indent)

    def warn(self, message: str, indent: int = 3):
        """Log warning message."""
        self.log(message, level="WARN", indent=indent)

    def debug(self, message: str, indent: int = 3):
        """Log debug message."""
        self.log(message, level="DEBUG", indent=indent)


# Global logger instance
_logger: Optional[PipelineLogger] = None


def get_logger() -> PipelineLogger:
    """Get or create global logger."""
    global _logger
    if _logger is None:
        _logger = PipelineLogger()
    return _logger


def init_logger(log_file: str = "experiments/run_log.txt"):
    """Initialize logger with custom path."""
    global _logger
    _logger = PipelineLogger(log_file)
