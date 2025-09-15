import logging
import sys
import os
import structlog

def setup_logging():
    """
    Configures structured logging for the application.
    - Human-readable logs for local development.
    - JSON logs for production (Lambda).
    """
    # print("--- Executing setup_logging() function ---")
    # These processors are shared between development and production
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Determine which renderer to use based on the environment
    if os.getenv("ENV") == "production":
        # print("--- prod flow ---")
        # Production JSON logs are best for CloudWatch
        processors = shared_processors + [
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
        log_level = logging.INFO
    else:
        # print("--- dev flow ---")
        # Development console logs are easier for humans to read
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
        log_level = logging.DEBUG

    # Configure the standard logging library to be a sink for structlog
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        force=True
    )

    # Configure structlog itself
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )