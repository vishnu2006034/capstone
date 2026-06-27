from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("app.exceptions")

class AppException(Exception):
    """Base application exception."""
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class EntityNotFoundError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            code="ENTITY_NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

class ComplianceViolationError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            code="COMPLIANCE_VIOLATION",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class IntegrationError(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            code="INTEGRATION_ERROR",
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )

# Exception handlers mapping
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning(f"AppException [{exc.code}] on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled Exception on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact system support.",
                "details": {}
            }
        }
    )
