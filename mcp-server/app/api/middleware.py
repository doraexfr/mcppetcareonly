import asyncio
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.exceptions import AppError, ErrorCode, error_response

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, timeout_seconds: int) -> None:
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content=error_response(
                    ErrorCode.TIMEOUT,
                    f"Request exceeded {self.timeout_seconds} seconds",
                ),
            )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(ErrorCode.VALIDATION_ERROR, str(exc)),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled request failure", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error_response("INTERNAL_ERROR", "Unexpected server error"),
        )

