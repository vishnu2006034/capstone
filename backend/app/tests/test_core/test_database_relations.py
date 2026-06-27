import pytest
from sqlalchemy.exc import IntegrityError
from app.models.models import User, Meeting, Task, TaskAssignment, TaskComment

def test_user_email_unique_constraint(db_session):
    # Insert first user
    user1 = User(name="User One", email="unique@company.com", role="Employee")
    db_session.add(user1)
    db_session.commit()
    
    # Try inserting second user with same email -> should raise IntegrityError
    user2 = User(name="User Two", email="unique@company.com", role="Employee")
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_meeting_cascade_deletes_tasks(db_session):
    # Setup owner user
    owner = User(name="Owner", email="owner@company.com", role="Manager")
    db_session.add(owner)
    db_session.commit()

    # Create meeting
    meeting = Meeting(title="Architecture Sync", status="Uploaded", uploaded_by=owner.id)
    db_session.add(meeting)
    db_session.flush()

    # Create task linked to meeting
    task = Task(meeting_id=meeting.id, title="Refactor DB schemas", status="InProgress")
    db_session.add(task)
    db_session.commit()

    # Confirm task exists
    assert db_session.query(Task).filter(Task.meeting_id == meeting.id).count() == 1

    # Delete meeting
    db_session.delete(meeting)
    db_session.commit()

    # Verify task was deleted automatically via cascade delete rules
    assert db_session.query(Task).filter(Task.meeting_id == meeting.id).count() == 0

def test_task_cascade_deletes_assignments_and_comments(db_session):
    # Setup users
    owner = User(name="Owner", email="owner2@company.com", role="Manager")
    assignee = User(name="Assignee", email="assignee@company.com", role="Employee")
    db_session.add_all([owner, assignee])
    db_session.commit()

    # Create meeting
    meeting = Meeting(title="Daily Standup", status="Uploaded", uploaded_by=owner.id)
    db_session.add(meeting)
    db_session.flush()

    # Create task
    task = Task(meeting_id=meeting.id, title="Fix scrollbars", status="InProgress")
    db_session.add(task)
    db_session.flush()

    # Create assignment and comment
    assignment = TaskAssignment(task_id=task.id, user_id=assignee.id)
    comment = TaskComment(task_id=task.id, user_id=assignee.id, content="Working on this.")
    db_session.add_all([assignment, comment])
    db_session.commit()

    # Verify records exist
    assert db_session.query(TaskAssignment).filter(TaskAssignment.task_id == task.id).count() == 1
    assert db_session.query(TaskComment).filter(TaskComment.task_id == task.id).count() == 1

    # Delete task
    db_session.delete(task)
    db_session.commit()

    # Verify task assignments and comments are cascade deleted
    assert db_session.query(TaskAssignment).filter(TaskAssignment.task_id == task.id).count() == 0
    assert db_session.query(TaskComment).filter(TaskComment.task_id == task.id).count() == 0
