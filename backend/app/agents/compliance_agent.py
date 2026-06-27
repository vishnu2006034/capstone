import logging
import json
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from google.antigravity import Agent, LocalAgentConfig
from app.models.models import Task, SOPDocument, ComplianceReport
from app.core.exceptions import EntityNotFoundError, AppException

logger = logging.getLogger("app.agents.compliance")

# Pydantic Schemas for Gemini Structured JSON Output
class ChecklistItem(BaseModel):
    item: str = Field(..., description="The specific SOP requirement item evaluated")
    passed: bool = Field(..., description="Whether the task description satisfies this requirement")

class SOPAuditResponse(BaseModel):
    status: str = Field(..., description="Overall status: PASSED, WARNING, or FAILED")
    checklist: List[ChecklistItem] = Field(default_factory=list, description="A granular checklist of evaluated requirements")
    missing_steps: List[str] = Field(default_factory=list, description="List of missing procedural steps detected in the task description")
    compliance_score: int = Field(..., description="Numeric compliance score from 0 (completely non-compliant) to 100 (fully compliant)")
    risk_level: str = Field(..., description="Determined operational risk: LOW, MEDIUM, HIGH, or CRITICAL")
    reasoning: str = Field(..., description="Detailed analytical justification explaining the compliance grading")


async def audit_task_against_sop(task_id: UUID, sop_id: UUID, db: Session) -> ComplianceReport:
    """
    Evaluates a task against an SOP document using Google ADK & Gemini.
    Stores the compliance checklist, score, risk, and reasoning in the database.
    """
    # 1. Fetch Task and SOP
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    sop = db.query(SOPDocument).filter(SOPDocument.id == sop_id).first()
    if not sop:
        raise EntityNotFoundError(message=f"SOP Document not found: {sop_id}")
        
    # Concatenate all SOP sections
    sections_text = ""
    for sec in sop.sections:
        sections_text += f"\nSection {sec.section_number or ''}: {sec.title or ''}\n{sec.content}\n"
        
    logger.info(f"Auditing task '{task.title}' against SOP '{sop.title}'")
    
    # 2. Construct Prompt
    prompt = f"""
    You are the SOP Compliance Agent. You audit task definitions against corporate Standard Operating Procedures (SOPs).
    
    Evaluate the proposed Task description against the provided SOP guidelines.
    Check if the Task has omitted any mandatory steps, validations, or prerequisite requirements listed in the SOP.
    
    TASK DETAILS:
    - Title: {task.title}
    - Description: {task.description or "No description provided"}
    
    SOP DOCUMENT DETAILS:
    - Title: {sop.title}
    - Department: {sop.department or "General"}
    - Version: {sop.version}
    
    SOP SECTIONS & GUIDELINES:
    \"\"\"
    {sections_text}
    \"\"\"
    
    Based on the guidelines, generate:
    1. Overall Status: PASSED (meets all rules), WARNING (minor omissions or check items missing but executable), or FAILED (severe violations or critical steps omitted).
    2. A checklist of key requirements evaluated and if they passed/failed.
    3. List of missing steps or guidelines.
    4. Compliance Score: Numeric rating from 0 (poor) to 100 (excellent).
    5. Risk Level: LOW, MEDIUM, HIGH, or CRITICAL based on omissions and task impact.
    6. Detailed reasoning trace.
    """
    
    # 3. Invoke Google ADK Agent
    config = LocalAgentConfig()
    async with Agent(config) as agent:
        response = await agent.chat(prompt, response_schema=SOPAuditResponse)
        response_text = await response.text()
        
        # 4. Parse Structured JSON response
        try:
            data = json.loads(response_text)
            audit_data = SOPAuditResponse(**data)
        except Exception as e:
            logger.error(f"Failed to parse structured JSON from compliance agent: {str(e)}. Raw: {response_text}")
            raise AppException(
                code="AGENT_PARSING_ERROR",
                message="Compliance Agent failed to return valid structured JSON report.",
                status_code=502
            )
            
        # Convert checklist and missing steps to JSON format for storage
        db_checklist = [item.model_dump() for item in audit_data.checklist]
        
        # 5. Persist Compliance Report
        report = ComplianceReport(
            task_id=task.id,
            status=audit_data.status.upper(),
            reasoning_trace=audit_data.reasoning,
            checklist=db_checklist,
            missing_steps=audit_data.missing_steps,
            compliance_score=audit_data.compliance_score,
            risk_level=audit_data.risk_level.upper()
        )
        
        db.add(report)
        
        # If audit failed, we can optionally change task status to Triage
        if audit_data.status.upper() == "FAILED":
            task.status = "Triage"
            db.add(task)
            
        db.commit()
        db.refresh(report)
        logger.info(f"Audited task {task_id}. Score: {audit_data.compliance_score}, Status: {audit_data.status}")
        
    return report
