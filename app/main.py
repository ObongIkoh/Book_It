import logging
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi.requests import Request

from app.db.session import get_db
from app.db import models
from sqlalchemy.orm import Session
from app.routers import auth, reviews, services, users, booking
from fastapi.middleware.cors import CORSMiddleware
from app.core.exceptions import BookItException, bookit_exception_handler
from app.core.exceptions import RequestValidationError, validation_exception_handler
from sqlalchemy.exc import SQLAlchemyError
from app.core.exceptions import (
    BookItException,
    bookit_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    general_exception_handler
)
from app.utils.logging import configure_logging
from app.core.config import settings  

configure_logging()
logger = logging.getLogger(__name__)
logger.info("Starting BookIt API initialization...")

# Define a database exception handler
def database_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"error": "Database error occurred."}
    )

# Define a general exception handler
def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred."}
    )

def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": True, "type": "ValidationError", "message": "Input validation failed."}
    )

# Initialize FastAPI app (Startup and shutdown events (on_event is deprecated in favor of lifespan in fastapi))
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Code before 'yield' runs on startup.
    Code after 'yield' runs on shutdown.
    """
    # 1. Startup Logic (Code before yield)
   
    logger.info(f"Starting {settings.project_name} v1.0.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    if settings.environment == "production":
        logger.info("Running in PRODUCTION mode")
        logger.info("API documentation disabled")
    else:
        logger.info(f"API documentation available at /docs")
    
    # Add connection pooling initialization here (e.g., init_database_pool())

    yield # Application runs here
    # 2. Shutdown Logic (Code after yield)
    
    logger.info(f"Shutting down {settings.project_name}")
    # Close database connections or clear cache here (e.g., close_database_pool())

app = FastAPI(
    title="BookIt API",
    description="BookIt API - Professional booking management system",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,  # Disable docs in production
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(services.router)
app.include_router(booking.router)
app.include_router(reviews.router)

# Exception handlers
app.add_exception_handler(BookItException, bookit_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code}")
    return response

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],   # Accept all headers
)

# Root and Health check endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the BookIt API"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Example endpoint: list users (even if table is empty)
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users