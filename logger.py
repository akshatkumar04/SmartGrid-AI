"""
SmartGrid AI — Structured Logging
==================================
Uses structlog for JSON-structured, context-aware logging.
Every log line carries correlation IDs, module, and environment context.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


def _add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject application-level metadata into every log record."""
    event_dict["app"] = "smartgrid_ai"
    event_dict["env"] = "development"
    return event_dict


def _drop_color_message_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Remove uvicorn's color_message key to keep logs clean."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    environment: str = "development",
) -> None:
    """
    Configure structlog for the entire application.
    Call once at application startup.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_app_context,
        _drop_color_message_key,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Silence noisy third-party loggers
    for noisy in ["urllib3", "asyncio", "aiohttp", "paho"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a bound logger instance for a module.

    Usage:
        logger = get_logger(__name__)
        logger.info("pipeline.start", records=1000, source="mqtt")
    """
    return structlog.get_logger(name)


class LogContext:
    """
    Context manager for adding temporary log context variables.

    Usage:
        with LogContext(request_id="abc123", meter_id="M-001"):
            logger.info("processing.reading")
    """

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def __enter__(self) -> "LogContext":
        structlog.contextvars.bind_contextvars(**self.kwargs)
        return self

    def __exit__(self, *args: Any) -> None:
        structlog.contextvars.unbind_contextvars(*self.kwargs.keys())


def log_duration(logger: structlog.stdlib.BoundLogger, operation: str):
    """Decorator that logs the wall-clock duration of a function."""
    import functools
    import time

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    f"{operation}.complete",
                    duration_ms=round(elapsed_ms, 2),
                )
                return result
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    f"{operation}.failed",
                    duration_ms=round(elapsed_ms, 2),
                    error=str(exc),
                )
                raise

        return wrapper

    return decorator