"""Logging setup and configuration."""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Literal, Optional

import structlog


def setup_logging(
    log_level: str = "INFO",
    log_format: Literal["json", "console"] = "json",
    log_dir: Optional[Path] = None,
) -> None:
    """Configure structured logging with structlog.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "console")
        log_dir: Directory for log files. If provided, logs will be written
            to files with daily rotation and 30-day retention.
    """
    # Shared processors for both formats
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure processors based on format
    if log_format == "json":
        formatter_processor = structlog.processors.JSONRenderer()
    else:  # console format
        formatter_processor = structlog.dev.ConsoleRenderer(colors=True)

    # Console formatter for file output (human-readable, no colors for text files)
    file_formatter_processor = structlog.dev.ConsoleRenderer(colors=False)

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=formatter_processor,
            foreign_pre_chain=shared_processors,
        )
    )

    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # File handler with daily rotation and 30-day retention
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "newsanalysis.log"

        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=file_formatter_processor,
                foreign_pre_chain=shared_processors,
            )
        )
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
