import logging
import sys

import structlog
from flask.logging import default_handler
from opensearchpy import TransportError
from structlog.contextvars import merge_contextvars

from constants.logging import (
    MESSAGE_ADS_SEARCH_FAILURE,
    MESSAGE_OPEN_SEARCH_FAILURE,
    MESSAGE_SCHEMA_VALIDATION_FAILURE,
    REQUEST_TYPE_FACETS,
)
from util.envvar import STAGE

# Configuring the system logger with Flask/WSGI-compatible settings
root = logging.getLogger()
root.addHandler(default_handler)
root.setLevel(logging.INFO)


def _configure():
    # Configuring structured logging
    base_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    if sys.stderr.isatty():
        log_processors = base_processors + [
            merge_contextvars,
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        log_processors = base_processors + [
            merge_contextvars,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    structlog.configure(
        log_processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    if not structlog.is_configured():
        _configure()
    return structlog.get_logger(name)


def log_record_for_transport_error(e: TransportError, method: str):
    return {
        "request_type": method,
        "os_status_code": e.status_code,
        "os_error": e.info,
        "message": MESSAGE_OPEN_SEARCH_FAILURE,
    }


def log_record_for_os_error(e: Exception, method: str):
    return {
        "request_type": method,
        "os_error": e,
        "message": MESSAGE_OPEN_SEARCH_FAILURE,
    }


def log_record_for_os_response_error(response_error, method):
    return {
        "request_type": method,
        "os_status_code": response_error.get("status"),
        "os_error": response_error.get("root_cause"),
        "message": MESSAGE_OPEN_SEARCH_FAILURE,
    }


def log_record_for_ads_error(e: Exception, method: str):
    return {
        "request_type": method,
        "ads_error": e,
        "message": MESSAGE_ADS_SEARCH_FAILURE,
    }


def log_record_for_schema_validation_error(e: Exception, method: str):
    return {
        "request_type": method,
        "schema_validation_error": e,
        "message": MESSAGE_SCHEMA_VALIDATION_FAILURE,
    }
