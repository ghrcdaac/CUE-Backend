import logging
import sys
import os
import structlog

def setup_logging():
    """
    Configures structured JSON logging for event-driven Lambda functions.
    This ensures logs are easily searchable and filterable in CloudWatch.
    """
    # Processors that add context to every log message
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Configure the standard logging library to be a sink for structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=os.getenv('LOG_LEVEL', 'INFO'),
    )

    # Configure structlog to output JSON
    structlog.configure(
        processors=shared_processors + [structlog.processors.JSONRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
