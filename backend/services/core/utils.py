#!/usr/bin/env python3
"""
Utility functions and logger for electricity analysis
"""
import os
import uuid
import inspect
from datetime import datetime
from typing import Optional
from backend.services.core.config import DEFAULT_LOGS_DIR


class ReportLogger:
    """Logger for report generation with session tracking"""
    def __init__(self, logs_dir: Optional[str] = None):
        self.session = uuid.uuid4().hex[:8]
        self.logs_dir = os.path.abspath(logs_dir or DEFAULT_LOGS_DIR)
        os.makedirs(self.logs_dir, exist_ok=True)

    def _get_caller_info(self) -> str:
        """Extract caller function, class, and line number from call stack"""
        # Skip: 0=current frame (_get_caller_info), 1=log method, 2=info/debug/warning/error, 3=actual caller
        frame = inspect.currentframe()
        try:
            if frame is None:
                return ""
            
            # Get the frame that called info/debug/warning/error (the actual user code)
            frame1 = frame.f_back
            if frame1 is None:
                return ""
            
            frame2 = frame1.f_back
            if frame2 is None:
                return ""
            
            caller_frame = frame2.f_back
            if caller_frame is None:
                return ""
            
            filename = os.path.basename(caller_frame.f_code.co_filename)
            line_number = caller_frame.f_lineno
            function_name = caller_frame.f_code.co_name
            
            # Try to get class name if it exists
            class_name = ""
            if 'self' in caller_frame.f_locals:
                instance = caller_frame.f_locals['self']
                class_name = instance.__class__.__name__ + "."
            elif 'cls' in caller_frame.f_locals:
                cls = caller_frame.f_locals['cls']
                class_name = cls.__name__ + "."
            
            return f"{filename}:{line_number} {class_name}{function_name}()"
        finally:
            del frame

    def format_message(self, level: str, msg: str, caller_info: str = "") -> str:
        """Format log message with timestamp, session, and caller information"""
        caller_str = f" | {caller_info}" if caller_info else ""
        return f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {self.session} [{level.upper()}] {caller_str} | {msg}\n"

    def log(self, level: str, msg: str):
        """Write log message to file"""
        caller_info = self._get_caller_info()
        formatted = self.format_message(level, msg, caller_info)
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


