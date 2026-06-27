from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler
)

# Initialize structured logging
setup_logging(settings.LOG_LEVEL)

# Boot FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Meeting-to-Execution agent pipeline.",
    version="0.1.0"
)

# Register routers
from app.api.v1 import api_router
app.include_router(api_router, prefix="/api/v1")

# Register custom middleware
app.add_middleware(RequestLoggingMiddleware)

# Register CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

@app.get("/")
def read_root():
    return {"message": "Welcome to Meeting2Execution AI API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "env": settings.ENV}
