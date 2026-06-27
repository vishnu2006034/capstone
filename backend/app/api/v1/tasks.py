import uuid
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, Body
from sqlalchemy.orm import Session
import sqlalchemy as sa

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError, AppException
from app.api.dependencies import get_current_user
from app.models.models import Task, TaskAssignment, TaskComment, User, Meeting
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut, CommentCreate, CommentOut
from app.core.events import trigger_task_assigned, trigger_task_completed

router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = logging.getLogger("app.api.v1.tasks")

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new task and registers assignments.
    """
    # Verify meeting exists
    meeting = db.query(Meeting).filter(Meeting.id == task_in.meeting_id).first()
    if not meeting:
        raise EntityNotFoundError(message=f"Meeting not found: {task_in.meeting_id}")
        
    new_task = Task(
        meeting_id=task_in.meeting_id,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority.upper(),
        status="Extracted",
        due_date=task_in.due_date
    )
    db.add(new_task)
    db.flush()  # populate new_task.id
    
    # Process assignments
    for email in task_in.assignee_emails:
        assignee = db.query(User).filter(User.email == email).first()
        if assignee:
            assignment = TaskAssignment(task_id=new_task.id, user_id=assignee.id)
            db.add(assignment)
        else:
            logger.warning(f"Failed to assign task: User with email {email} does not exist.")
            
    db.commit()
    db.refresh(new_task)
    
    # Trigger TASK_ASSIGNED alerts
    for assignment in new_task.assignments:
        trigger_task_assigned(new_task.id, assignment.user_id, db)
        
    # Build assignees list for schema serialization
    task_out = TaskOut.model_validate(new_task)
    task_out.assignees = [a.assignee for a in new_task.assignments]
    return task_out

@router.get("", response_model=List[TaskOut])
def list_tasks(
    meeting_id: Optional[UUID] = Query(None),
    assignee_id: Optional[UUID] = Query(None),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves tasks with filtering, full-text search, and pagination.
    """
    query = db.query(Task)
    
    # 1. Filters
    if meeting_id:
        query = query.filter(Task.meeting_id == meeting_id)
    if priority:
        query = query.filter(Task.priority == priority.upper())
    if status:
        query = query.filter(Task.status == status)
    if assignee_id:
        query = query.join(TaskAssignment).filter(TaskAssignment.user_id == assignee_id)
        
    # 2. Search
    if search:
        query = query.filter(
            sa.or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%")
            )
        )
        
    # 3. Order & Pagination
    query = query.order_by(Task.created_at.desc())
    tasks = query.offset((page - 1) * limit).limit(limit).all()
    
    # Map assignees & comments
    results = []
    for task in tasks:
        task_out = TaskOut.model_validate(task)
        task_out.assignees = [a.assignee for a in task.assignments]
        task_out.comments = [
            CommentOut.model_validate(c) for c in task.comments
        ]
        results.append(task_out)
        
    return results

@router.get("/{task_id}", response_model=TaskOut)
def get_task_details(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves detailed task records including assignees and comments.
    """
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    task = db.query(Task).filter(Task.id == task_uuid).first()
    if not task:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    task_out = TaskOut.model_validate(task)
    task_out.assignees = [a.assignee for a in task.assignments]
    task_out.comments = [CommentOut.model_validate(c) for c in task.comments]
    return task_out

@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates task fields.
    """
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    task = db.query(Task).filter(Task.id == task_uuid).first()
    if not task:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    old_status = task.status
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    db.commit()
    db.refresh(task)
    
    # Trigger TASK_COMPLETED alert
    if old_status != "Done" and task.status == "Done":
        trigger_task_completed(task.id, db)
        
    task_out = TaskOut.model_validate(task)
    task_out.assignees = [a.assignee for a in task.assignments]
    task_out.comments = [CommentOut.model_validate(c) for c in task.comments]
    return task_out

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a task and cascades deletions.
    """
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    task = db.query(Task).filter(Task.id == task_uuid).first()
    if not task:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    db.delete(task)
    db.commit()
    return None

@router.post("/{task_id}/assign", response_model=TaskOut)
def assign_task(
    task_id: str,
    emails: List[str] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assigns a task to users specified by email addresses.
    """
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    task = db.query(Task).filter(Task.id == task_uuid).first()
    if not task:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    # Process assignments
    for email in emails:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise AppException(
                code="USER_NOT_FOUND",
                message=f"User with email {email} not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
            
        # Check if already assigned
        existing = db.query(TaskAssignment).filter(
            TaskAssignment.task_id == task_uuid,
            TaskAssignment.user_id == user.id
        ).first()
        
        if not existing:
            assignment = TaskAssignment(task_id=task_uuid, user_id=user.id)
            db.add(assignment)
            
    db.commit()
    db.refresh(task)
    
    # Trigger TASK_ASSIGNED alerts
    for a in task.assignments:
        trigger_task_assigned(task.id, a.user_id, db)
        
    task_out = TaskOut.model_validate(task)
    task_out.assignees = [a.assignee for a in task.assignments]
    task_out.comments = [CommentOut.model_validate(c) for c in task.comments]
    return task_out

@router.post("/{task_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_task_comment(
    task_id: str,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Appends a new comment to the task.
    """
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    task = db.query(Task).filter(Task.id == task_uuid).first()
    if not task:
        raise EntityNotFoundError(message=f"Task not found: {task_id}")
        
    new_comment = TaskComment(
        task_id=task_uuid,
        user_id=current_user.id,
        content=comment_in.content
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment
