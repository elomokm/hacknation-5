"""Global exception handlers — surface honest error context to clients."""

import logging
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


_MODULE_PATTERNS = [
    (re.compile(r"/profile/"), "module_01_skills"),
    (re.compile(r"/risk/"), "module_02_risk"),
    (re.compile(r"/opportunities/"), "module_03_opportunity"),
    (re.compile(r"/config/"), "core_config"),
    (re.compile(r"/health"), "core_health"),
]


def _infer_module(path: str) -> str:
    """Map a request URL path to its source module name."""
    for pattern, module in _MODULE_PATTERNS:
        if pattern.search(path):
            return module
    return "unknown"


def _structured_error(
    status: int,
    error: str,
    detail: str,
    request: Request,
    limitations_note: str | None = None,
) -> JSONResponse:
    """Build a structured error response."""
    body = {
        "error": error,
        "detail": detail,
        "module": _infer_module(request.url.path),
        "path": request.url.path,
    }
    if limitations_note:
        body["limitations_note"] = limitations_note
    return JSONResponse(status_code=status, content=body)


async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning("ValueError on %s: %s", request.url.path, exc)
    return _structured_error(400, "ValueError", str(exc), request)


async def _file_not_found_handler(
    request: Request, exc: FileNotFoundError
) -> JSONResponse:
    logger.error("Missing file on %s: %s", request.url.path, exc)
    return _structured_error(
        500, "FileNotFoundError", str(exc), request,
        limitations_note="Required data file is missing on the server.",
    )


async def _key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    logger.warning("KeyError on %s: %s", request.url.path, exc)
    return _structured_error(404, "KeyError", str(exc), request)


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled %s on %s", type(exc).__name__, request.url.path)
    return _structured_error(
        500,
        type(exc).__name__,
        str(exc) or "Internal server error",
        request,
        limitations_note=(
            "UNMAPPED is honest about its limits — this error has been logged. "
            "If it relates to data, see DATA_SOURCES.md for known gaps."
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire custom exception handlers onto the FastAPI app."""
    app.add_exception_handler(ValueError, _value_error_handler)
    app.add_exception_handler(FileNotFoundError, _file_not_found_handler)
    app.add_exception_handler(KeyError, _key_error_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
