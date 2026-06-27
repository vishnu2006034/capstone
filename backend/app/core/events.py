import logging
from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
import asyncio

from app.models.models import Task, SOPDocument, User, Notification, ComplianceReport, Meeting
from app.agents.meeting_agent import extract_tasks_from_transcript
from app.agents.compliance_agent import audit_task_against_sop

logger = logging.getLogger("app.core.events")

# Helper function to run async agent tasks in synchronous FastAPI background threads
def run_async_task(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Schedule in the running event loop
        asyncio.ensure_future(coro)
    else:
        loop.run_until_complete(coro)


async def handle_meeting_uploaded(meeting_id: UUID, db: Session):
    """
    Triggered when a transcript is uploaded. Extracts tasks using MIA,
    then automatically triggers SOP Compliance audits for each extracted task.
    """
    logger.info(f"[Trigger] MEETING_UPLOADED received for meeting {meeting_id}")
    try:
        # 1. Run MIA task extraction
        tasks = await extract_tasks_from_transcript(meeting_id, db)
        logger.info(f"[Trigger] Extracted {len(tasks)} tasks from meeting {meeting_id}")
        
        # 2. Automatically find relevant SOPs for the meeting/tasks and audit
        # We will find the latest SOP for the task's department or generic SOPs
        for task in tasks:
            # For demo, match latest DevOps or Engineering SOP, otherwise audit against the first SOP
            sop = db.query(SOPDocument).order_by(SOPDocument.created_at.desc()).first()
            if sop:
                await audit_task_against_sop(task.id, sop.id, db)
                logger.info(f"[Trigger] Auto-audited task {task.id} against SOP {sop.id}")
    except Exception as e:
        logger.error(f"Error executing MEETING_UPLOADED workflow: {str(e)}", exc_info=True)


async def handle_sop_uploaded(sop_id: UUID, db: Session):
    """
    Triggered when a new SOP is uploaded. Automatically re-audits all pending or triaged
    tasks belonging to the same department.
    """
    logger.info(f"[Trigger] SOP_UPLOADED received for SOP {sop_id}")
    try:
        sop = db.query(SOPDocument).filter(SOPDocument.id == sop_id).first()
        if not sop:
            return
            
        # Scan for active tasks to evaluate against new SOP
        tasks = db.query(Task).filter(
            Task.status.in_(["Extracted", "Triage", "InProgress"])
        ).all()
        
        logger.info(f"[Trigger] Found {len(tasks)} tasks in department '{sop.department}' to re-audit.")
        for task in tasks:
            await audit_task_against_sop(task.id, sop.id, db)
    except Exception as e:
        logger.error(f"Error executing SOP_UPLOADED workflow: {str(e)}", exc_info=True)


def trigger_meeting_uploaded(meeting_id: UUID, db: Session, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_async_task, handle_meeting_uploaded(meeting_id, db))

def trigger_sop_uploaded(sop_id: UUID, db: Session, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_async_task, handle_sop_uploaded(sop_id, db))

def trigger_task_assigned(task_id: UUID, user_id: UUID, db: Session):
    """
    Triggered when a task is assigned to a user. Creates a notification.
    """
    logger.info(f"[Trigger] TASK_ASSIGNED: Task {task_id} assigned to user {user_id}")
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        notify = Notification(
            user_id=user_id,
            title="New Task Assignment",
            content=f"You have been assigned to task: '{task.title}'",
            is_read=False
        )
        db.add(notify)
        db.commit()

def trigger_task_completed(task_id: UUID, db: Session):
    """
    Triggered when a task status is changed to Done. Alerts the meeting owner/manager.
    """
    logger.info(f"[Trigger] TASK_COMPLETED: Task {task_id} marked as completed.")
    task = db.query(Task).filter(Task.id == task_id).first()
    if task and task.meeting:
        meeting_creator_id = task.meeting.uploaded_by
        if meeting_creator_id:
            notify = Notification(
                user_id=meeting_creator_id,
                title="Task Completed",
                content=f"The task '{task.title}' from meeting '{task.meeting.title}' is completed.",
                is_read=False
            )
            db.add(notify)
            db.commit()

def trigger_compliance_violation(report_id: UUID, db: Session):
    """
    Triggered when a compliance check fails. Alerts managers and compliance officers.
    """
    logger.info(f"[Trigger] COMPLIANCE_VIOLATION: Report {report_id} failed.")
    report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
    if report and report.task:
        # Alert all managers and compliance officers
        managers = db.query(User).filter(User.role.in_(["Manager", "Compliance Officer", "Admin"])).all()
        for manager in managers:
            notify = Notification(
                user_id=manager.id,
                title="[VIOLATION] SOP Compliance Breach",
                content=f"Task '{report.task.title}' failed compliance check. Compliance Score: {report.compliance_score}. Risk Level: {report.risk_level}.",
                is_read=False
            )
            db.add(notify)
        db.commit()

def trigger_deadline_approaching(db: Session):
    """
    Triggered by scheduler. Alerts assignees of tasks due within 24 hours.
    """
    logger.info("[Trigger] Running DEADLINE_APPROACHING scan...")
    now = datetime.now(timezone.utc)
    warning_threshold = now + timedelta(hours=24)
    
    # Query tasks due within next 24 hours that are not Done
    tasks = db.query(Task).filter(
        Task.due_date > now,
        Task.due_date <= warning_threshold,
        Task.status != "Done"
    ).all()
    
    logger.info(f"[Trigger] Found {len(tasks)} tasks approaching deadline.")
    for task in tasks:
        for assignment in task.assignments:
            # Create notification
            notify = Notification(
                user_id=assignment.user_id,
                title="[URGENT] Deadline Approaching",
                content=f"Your task '{task.title}' is due by {task.due_date.isoformat()}.",
                is_read=False
            )
            db.add(notify)
    db.commit()
