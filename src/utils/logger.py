"""
Logger utility for the application
"""
import sys
from datetime import datetime
from typing import Any
from pathlib import Path
from src.models.types import PATHS

class Logger:
    """Logger class for consistent logging across the application"""
    _log_file_path = PATHS.LOGS / "app.log"
    _debug_log_file_path = PATHS.LOGS / "debug.log"
    
    @staticmethod
    def _write_to_file(message: str):
        try:
            Logger._log_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(Logger._log_file_path, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception:
            # Avoid raising in logging
            pass
    
    @staticmethod
    def _write_to_debug_file(message: str):
        try:
            Logger._debug_log_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(Logger._debug_log_file_path, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception:
            # Avoid raising in logging
            pass
    
    @staticmethod
    def _timestamp():
        """Get current timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    @staticmethod
    def header(message: str):
        """Log a header message"""
        text1 = f"\n{'='*60}"
        text2 = f"🚀 {message}"
        text3 = f"{'='*60}"
        print(text1)
        print(text2)
        print(text3)
        Logger._write_to_file(text1)
        Logger._write_to_file(text2)
        Logger._write_to_file(text3)
    
    @staticmethod
    def step(step_number: int, message: str):
        """Log a step message"""
        text1 = f"\n📋 Step {step_number}: {message}"
        text2 = f"{'─'*50}"
        print(text1)
        print(text2)
        Logger._write_to_file(text1)
        Logger._write_to_file(text2)
    
    @staticmethod
    def info(message: str):
        """Log an info message"""
        text = f"[{Logger._timestamp()}] ℹ️  {message}"
        print(text)
        Logger._write_to_file(text)
        # Duplicate INFO logs into debug.log as requested
        Logger._write_to_debug_file(text)
    
    @staticmethod
    def success(message: str):
        """Log a success message"""
        text = f"[{Logger._timestamp()}] ✅ {message}"
        print(text)
        Logger._write_to_file(text)
    
    @staticmethod
    def warning(message: str):
        """Log a warning message"""
        text = f"[{Logger._timestamp()}] ⚠️  {message}"
        print(text)
        Logger._write_to_file(text)
    
    @staticmethod
    def error(message: str, error: Any = None):
        """Log an error message"""
        if error:
            text = f"[{Logger._timestamp()}] ❌ {message}: {error}"
        else:
            text = f"[{Logger._timestamp()}] ❌ {message}"
        print(text)
        Logger._write_to_file(text)
    
    @staticmethod
    def debug(message: str):
        """Log a debug message"""
        text = f"[{Logger._timestamp()}] 🐛 {message}"
        print(text)
        Logger._write_to_file(text)
    
    @staticmethod
    def progress(current: int, total: int, message: str = ""):
        """Log progress"""
        percentage = (current / total) * 100
        bar_length = 30
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        text = f"[{bar}] {percentage:.1f}% {message}"
        print(f"\r{text}", end='', flush=True)
        Logger._write_to_file(text)
        if current == total:
            print()  # New line when complete 