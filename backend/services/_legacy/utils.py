#!/usr/bin/env python3
"""
Utility functions and logger for electricity analysis
"""
import os
import uuid
from datetime import datetime
from typing import Optional
from .config import DEFAULT_LOGS_DIR


class ReportLogger:
    """Logger for report generation with session tracking"""
    def __init__(self, logs_dir: Optional[str] = None):
        self.session = uuid.uuid4().hex[:8]
        self.logs_dir = os.path.abspath(logs_dir or DEFAULT_LOGS_DIR)
        os.makedirs(self.logs_dir, exist_ok=True)

    def format_message(self, level: str, msg: str) -> str:
        """Format log message with timestamp and session"""
        return f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self.session} [{level.upper()}] {msg}\n"

    def log(self, level: str, msg: str):
        """Write log message to file"""
        formatted = self.format_message(level, msg)
        log_path = os.path.join(self.logs_dir, f"{level}.txt")
        with open(log_path, "a") as f:
            f.write(formatted)

    def info(self, msg: str):
        self.log('info', msg)

    def debug(self, msg: str):
        self.log('debug', msg)

    def warning(self, msg: str):
        self.log('warning', msg)

    def error(self, msg: str):
        self.log('error', msg)

    def get_html(self, levels=('info', 'warning', 'error', 'debug')) -> str:
        """Get HTML representation of logs for current session"""
        html = ""
        for level in levels:
            log_path = os.path.join(self.logs_dir, f"{level}.txt")
            try:
                with open(log_path, "r") as f:
                    # Select lines that contain the session
                    lines = [line for line in f.readlines() if self.session in line]
                if lines:
                    # Remove the session from the message
                    lines = [line.replace(f'{self.session} - ', '') for line in lines]
                    html += f"<h2>{level.capitalize()}</h2><ul>"
                    for msg in lines:
                        html += f"<li>{msg}</li>"
                    html += "</ul>"
            except FileNotFoundError:
                continue
        return html


def raise_with_context(message: str, original_error: Optional[Exception] = None) -> None:
    """Raise a RuntimeError with optional chained context."""
    if original_error is None:
        raise RuntimeError(message)
    raise RuntimeError(f"{message}: {original_error}") from original_error


def generate_power_column_name(load_name: str) -> str:
    """Return standardized power column label."""
    return f"{load_name.strip()} [kW]"


def generate_consumption_column_name(load_name: str) -> str:
    """Return standardized consumption column label."""
    return f"{load_name.strip()} [kWh]"

