import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException

from app.core.logger import get_logger

logger = get_logger(__name__)


class ApplicationError(Exception):
    """Base exception for application-specific errors."""

    def __init__(self, status_code: int = 500, detail: str = "Internal server error"):
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)


class CustomValidationError(Exception):
    """Exception for validation errors."""

    def __init__(
        self,
        status_code: int = 422,
        error: str = "Validation error",
        location: str | None = None,
    ):
        self.status_code = status_code
        self.detail = {
            "error": error,
            "location": location,
        }
        super().__init__(self.detail)


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers for FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(  # noqa: RUF029
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors from request data."""
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "path": request.url.path,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ):  # noqa: RUF029
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "detail": exc.detail,
                "path": request.url.path,
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(  # noqa: RUF029
        request: Request, exc: ValidationError
    ):
        """Handle Pydantic validation errors."""
        logger.error(f"Pydantic validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "path": request.url.path,
            },
        )

    @app.exception_handler(CustomValidationError)
    async def custom_validation_error_handler(  # noqa: RUF029
        request: Request, exc: CustomValidationError
    ):
        """Handle custom validation errors."""
        logger.error(f"Custom validation error: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Validation Error",
                "detail": exc.detail,
                "path": request.url.path,
            },
        )

    @app.exception_handler(ApplicationError)
    async def app_exception_handler(
        request: Request, exc: ApplicationError
    ):  # noqa: RUF029
        """Handle application-specific exceptions."""
        logger.error(f"Application error: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "Application Error",
                "detail": exc.detail,
                "path": request.url.path,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ):  # noqa: RUF029
        """Handle any unhandled exceptions."""
        logger.error(f"Unhandled exception: {exc!s}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": (
                    "An unexpected error occurred"
                    if not isinstance(exc, ApplicationError)
                    else str(exc)
                ),
                "path": request.url.path,
            },
        )
