from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.sops import router as sops_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(meetings_router)
api_router.include_router(tasks_router)
api_router.include_router(sops_router)
