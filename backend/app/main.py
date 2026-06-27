from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Meeting-to-Execution agent pipeline.",
    version="0.1.0"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Meeting2Execution AI API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "env": settings.ENV}
