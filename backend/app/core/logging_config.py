"""
Centralized Logging Configuration for AI YouTuber Studio

Provides standardized logging setup for the entire application including:
- Console and file handlers with rotation
- Structured log formatting with timestamps and context
- Request ID tracking for correlation
- Environment-based log levels
- Performance metric logging
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid
from contextvars import ContextVar

# Context variable for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """Add request ID to log records for correlation"""

    def filter(self, record):
        record.request_id = request_id_var.get() or "N/A"
        return True


class ColoredFormatter(logging.Formatter):
    """Colored console output for better readability"""

    COLORS = {
        'DEBUG': '\033[0;36m',  # Cyan
        'INFO': '\033[0;32m',  # Green
        'WARNING': '\033[1;33m',  # Yellow
        'ERROR': '\033[0;31m',  # Red
        'CRITICAL': '\033[1;35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_level: str = None,
    log_file: str = None,
    enable_file_logging: bool = True,
    enable_colored_output: bool = True
):
    """
    Configure application-wide logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: logs/app.log)
        enable_file_logging: Whether to write logs to file
        enable_colored_output: Whether to use colored console output

    Returns:
        Configured root logger
    """
    # Determine log level from environment or parameter
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Create logs directory
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Default log file path
    if log_file is None:
        log_file = log_dir / "app.log"
    else:
        log_file = Path(log_file)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if enable_colored_output and sys.stdout.isatty():
        console_format = ColoredFormatter(
            fmt='[%(asctime)s] [%(levelname)s] [req:%(request_id)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_format = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)-8s] [req:%(request_id)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_format)
    console_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(console_handler)

    # File handler with rotation (if enabled)
    if enable_file_logging:
        # Rotating file handler: max 10MB per file, keep 5 backups
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)

        file_format = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)-8s] [req:%(request_id)s] [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        file_handler.addFilter(RequestIDFilter())
        root_logger.addHandler(file_handler)

        # Error file handler - separate file for errors only
        error_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        error_handler.addFilter(RequestIDFilter())
        root_logger.addHandler(error_handler)

    # Reduce verbosity of some third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google.auth").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root_logger.info("=" * 80)
    root_logger.info(f"Logging initialized - Level: {log_level}, File: {log_file if enable_file_logging else 'disabled'}")
    root_logger.info("=" * 80)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None):
    """
    Set request ID for current context (for log correlation).

    Args:
        request_id: Request ID to set, or None to generate new UUID
    """
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get current request ID from context"""
    return request_id_var.get()


def clear_request_id():
    """Clear request ID from context"""
    request_id_var.set(None)


# Performance logging helper
class LogExecutionTime:
    """Context manager to log execution time of code blocks"""

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(self.level, f"{self.operation} - Started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds() * 1000
        if exc_type is None:
            self.logger.log(self.level, f"{self.operation} - Completed in {duration:.2f}ms")
        else:
            self.logger.error(f"{self.operation} - Failed after {duration:.2f}ms: {exc_val}")
        return False  # Don't suppress exceptions


# Convenience decorators for timing
def log_execution_time(operation_name: str = None):
    """
    Decorator to log execution time of functions.

    Usage:
        @log_execution_time("Process video")
        def process_video(video_id):
            ...
    """
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"

        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start_time = datetime.now()
            logger.info(f"{operation_name} - Started")

            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"{operation_name} - Completed in {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(f"{operation_name} - Failed after {duration:.2f}ms: {e}", exc_info=True)
                raise

        return wrapper
    return decorator


# Initialize logging when module is imported
if __name__ != "__main__":
    # Auto-initialize with defaults when imported
    setup_logging()
