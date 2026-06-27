from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_user, RoleChecker
from app.models.models import User
from app.schemas.copilot import CopilotQuery, CopilotResponse
from app.agents.copilot_agent import ask_manager_copilot

router = APIRouter(prefix="/copilot", tags=["Manager Copilot"])

# Only Admins and Managers can consult the Copilot
allow_admin_or_manager = RoleChecker(["Admin", "Manager"])

@router.post("/query", response_model=CopilotResponse)
async def query_copilot(
    query_in: CopilotQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_admin_or_manager)
):
    """
    Exposes manager copilot reasoning queries. Returns natural language insights
    regarding overdue tasks, overloaded employees, violating SOPs, or meeting workloads.
    """
    answer = await ask_manager_copilot(query_in.query, db)
    return CopilotResponse(answer=answer)
