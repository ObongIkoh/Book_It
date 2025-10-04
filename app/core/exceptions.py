
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

class BookItException(Exception):
    """Base exception class for BookIt application"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(BookItException):
    """Raised when data validation fails"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class AuthenticationError(BookItException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)

class AuthorizationError(BookItException):
    """Raised when authorization fails"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)

class NotFoundError(BookItException):
    """Raised when resource is not found"""
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)

class ConflictError(BookItException):
    """Raised when there's a conflict (like booking overlap)"""
    def __init__(self, message: str):
        super().__init__(message, status_code=409)

class DatabaseError(BookItException):
    """Raised when database operations fail"""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status_code=500)

async def bookit_exception_handler(request: Request, exc: BookItException):
    """Handler for custom BookIt exceptions"""
    logger.error(f"BookIt Exception: {exc.message} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "type": exc.__class__.__name__
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for Pydantic validation errors"""
    logger.warning(f"Validation Error: {exc} - Path: {request.url.path}")
    
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Invalid input data",
            "details": errors,
            "type": "ValidationError"
        }
    )

async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler for database errors"""
    logger.error(f"Database Error: {str(exc)} - Path: {request.url.path}")
    
    if isinstance(exc, IntegrityError):
        # Handle unique constraint violations
        if "email" in str(exc.orig).lower():
            message = "Email address is already registered"
        elif "unique" in str(exc.orig).lower():
            message = "This record already exists"
        else:
            message = "Data integrity constraint violated"
    else:
        message = "Database operation failed"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": message,
            "type": "DatabaseError"
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handler for unhandled exceptions"""
    logger.error(f"Unhandled Exception: {str(exc)} - Path: {request.url.path}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "An unexpected error occurred. Please try again later.",
            "type": "InternalServerError"
        }
    )
