import logging
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import sqlalchemy as sa

from google.antigravity import Agent, LocalAgentConfig
from app.models.models import Task, ComplianceReport, Notification, AuditLog, User
from app.core.exceptions import AppException

logger = logging.getLogger("app.agents.auditor")

class AlertItem(BaseModel):
    assignee_email: Optional[str] = Field(None, description="Email of the user to alert (if specific task owner)")
    title: str = Field(..., description="Short subject of the alert")
    message: str = Field(..., description="Detailed description of the operational issue")
    severity: str = Field("WARNING", description="INFO, WARNING, or CRITICAL")

class OperationsAuditResponse(BaseModel):
    alerts: List[AlertItem] = Field(default_factory=list)
    violations_summary: str = Field(..., description="Summary of policy violations detected")
    remediation_plan: str = Field(..., description="Actionable step-by-step remediation advice for leadership")


async def run_operations_audit(db: Session) -> dict:
    """
    Scans the database for overdue tasks, compliance violations, and missing approvals.
    Uses Google ADK to analyze bottlenecks, creates database Notification alerts, 
    and logs the audit report.
    """
    logger.info("Executing automated operations audit scan...")
    now = datetime.now(timezone.utc)
    
    # 1. Query Overdue Tasks (due date passed and status not Done)
    overdue_tasks = db.query(Task).filter(
        Task.due_date < now,
        Task.status != "Done"
    ).all()
    
    # 2. Query Policy Violations (failed compliance checks)
    violations = db.query(Task).join(ComplianceReport).filter(
        ComplianceReport.status == "FAILED"
    ).all()
    
    # 3. Query Missing Approvals (tasks in Triage status requiring attention)
    triage_tasks = db.query(Task).filter(
        Task.status == "Triage"
    ).all()
    
    total_issues = len(overdue_tasks) + len(violations) + len(triage_tasks)
    if total_issues == 0:
        logger.info("No operational issues detected. Skipping agent audit.")
        # Log empty audit run
        log = AuditLog(
            action="OPERATIONS_AUDIT_PASS",
            details={"timestamp": now.isoformat(), "message": "All operations aligned. 0 issues detected."}
        )
        db.add(log)
        db.commit()
        return {"status": "SUCCESS", "issues_detected": 0, "alerts_sent": 0}
        
    # Compile issue report for the agent
    report_text = f"CURRENT TIMESTAMP: {now.isoformat()}\n\n"
    
    if overdue_tasks:
        report_text += "--- OVERDUE TASKS ---\n"
        for t in overdue_tasks:
            assignees = ", ".join([a.assignee.email for a in t.assignments])
            report_text += f"- Task: {t.title} | Due: {t.due_date} | Status: {t.status} | Assignees: {assignees}\n"
            
    if violations:
        report_text += "\n--- COMPLIANCE VIOLATIONS ---\n"
        for t in violations:
            last_report = t.compliance_reports[-1] if t.compliance_reports else None
            reasoning = last_report.reasoning_trace if last_report else "No trace"
            report_text += f"- Task: {t.title} | Priority: {t.priority} | Audit Status: FAILED | Reasoning: {reasoning}\n"
            
    if triage_tasks:
        report_text += "\n--- TASKS REQUIRING APPROVAL / TRIAGE ---\n"
        for t in triage_tasks:
            report_text += f"- Task: {t.title} | Status: {t.status} | Priority: {t.priority}\n"
            
    # 4. Invoke Google ADK Agent
    prompt = f"""
    You are the Operations Auditor Agent. You scan company workspaces, track overdue milestones, flag compliance violations, and generate alerts.
    
    Analyze the following operational report containing issues flagged in our database:
    
    {report_text}
    
    For each issue:
    1. Identify the impact and severity.
    2. Generate structured alerts, routing them to the task's assignee email. If no assignee is listed, route it to general management (leave email blank).
    3. Formulate a consolidated summary of violations.
    4. Compile an actionable remediation plan for team leads.
    """
    
    config = LocalAgentConfig()
    async with Agent(config) as agent:
        response = await agent.chat(prompt, response_schema=OperationsAuditResponse)
        response_text = await response.text()
        
        try:
            data = json.loads(response_text)
            audit_response = OperationsAuditResponse(**data)
        except Exception as e:
            logger.error(f"Failed to parse structured JSON from Operations Auditor Agent: {str(e)}")
            raise AppException(
                code="AGENT_PARSING_ERROR",
                message="Auditor Agent failed to return valid JSON report.",
                status_code=502
            )
            
        alerts_created = 0
        # 5. Persist Alerts (Notifications)
        for alert in audit_response.alerts:
            target_user = None
            if alert.assignee_email:
                target_user = db.query(User).filter(User.email == alert.assignee_email).first()
                
            # If no user matches or is specified, fallback to notify all Managers/Admins
            if not target_user:
                managers = db.query(User).filter(User.role.in_(["Manager", "Admin"])).all()
                for manager in managers:
                    notify = Notification(
                        user_id=manager.id,
                        title=f"[Ops Audit] {alert.title}",
                        content=alert.message,
                        is_read=False
                    )
                    db.add(notify)
                    alerts_created += 1
            else:
                notify = Notification(
                    user_id=target_user.id,
                    title=alert.title,
                    content=alert.message,
                    is_read=False
                )
                db.add(notify)
                alerts_created += 1
                
        # 6. Persist Audit Report Log
        audit_log = AuditLog(
            action="OPERATIONS_AUDIT_RUN",
            details={
                "timestamp": now.isoformat(),
                "violations_summary": audit_response.violations_summary,
                "remediation_plan": audit_response.remediation_plan,
                "overdue_count": len(overdue_tasks),
                "violations_count": len(violations),
                "triage_count": len(triage_tasks),
                "alerts_sent": alerts_created
            }
        )
        db.add(audit_log)
        
        db.commit()
        logger.info(f"Operations audit completed. Created {alerts_created} notifications.")
        
        return {
            "status": "SUCCESS",
            "issues_detected": total_issues,
            "alerts_sent": alerts_created,
            "violations_summary": audit_response.violations_summary,
            "remediation_plan": audit_response.remediation_plan
        }
