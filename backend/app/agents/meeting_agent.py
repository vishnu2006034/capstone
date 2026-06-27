import logging
import uuid
import json
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from google.antigravity import Agent, LocalAgentConfig
from app.models.models import Meeting, Transcript, Task, TaskAssignment, User
from app.core.exceptions import EntityNotFoundError, AppException

logger = logging.getLogger("app.agents.meeting")

# Pydantic Schemas for Gemini Structured JSON Output
class ExtractedTaskItem(BaseModel):
    title: str = Field(..., description="Short summary of the task")
    description: str = Field(..., description="Detailed description of the task requirements")
    assignee_email: Optional[str] = Field(None, description="Email of the owner/assignee mentioned in the transcript")
    priority: str = Field("MEDIUM", description="LOW, MEDIUM, HIGH, or CRITICAL")
    due_date: Optional[str] = Field(None, description="RFC-3339 format due date string if mentioned, else null")
    risks: Optional[str] = Field(None, description="Any identified risks or warning notes related to this task")
    dependencies: List[str] = Field(default_factory=list, description="List of other tasks this task depends on")

class ExtractedTasksResponse(BaseModel):
    tasks: List[ExtractedTaskItem]


async def extract_tasks_from_transcript(meeting_id: UUID, db: Session) -> List[Task]:
    """
    Reads the meeting transcript, extracts tasks via Google ADK & Gemini,
    and persists them to the PostgreSQL database.
    """
    # 1. Fetch meeting & transcript
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")
        
    transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
    if not transcript or not transcript.raw_text:
        raise AppException(
            code="MISSING_TRANSCRIPT",
            message="No transcript text available for this meeting to extract tasks.",
            status_code=400
        )
        
    logger.info(f"Extracting tasks for meeting: {meeting.title} ({meeting_id})")
    
    # 2. Construct the prompt for the ADK Agent
    prompt = f"""
    You are the Meeting Intelligence Agent. You analyze meeting transcripts and extract structured action items.
    
    Analyze the following meeting transcript and extract all agreed-upon action items, tasks, and responsibilities.
    For each task, extract:
    - Title: Short descriptive name.
    - Description: Detailed technical context.
    - Owner/Assignee: Extract their corporate email if mentioned or implied.
    - Deadline: Specific target date/time if discussed (convert relative terms like 'by next Tuesday' to expected dates).
    - Priority: LOW, MEDIUM, HIGH, or CRITICAL based on dialogue urgency.
    - Risks: Flags, safety concerns, or architectural blockers.
    - Dependencies: Other tasks or prerequisites mentioned.
    
    Meeting Title: {meeting.title}
    Meeting Scheduled Time: {meeting.scheduled_time}
    
    Transcript:
    \"\"\"
    {transcript.raw_text}
    \"\"\"
    """
    
    # 3. Invoke Google ADK Agent
    config = LocalAgentConfig()
    created_tasks = []
    
    async with Agent(config) as agent:
        response = await agent.chat(prompt, response_schema=ExtractedTasksResponse)
        response_text = await response.text()
        
        # 4. Parse structured JSON response
        try:
            data = json.loads(response_text)
            extracted_response = ExtractedTasksResponse(**data)
        except Exception as e:
            logger.error(f"Failed to parse structured JSON from agent: {str(e)}. Raw output: {response_text}")
            raise AppException(
                code="AGENT_PARSING_ERROR",
                message="Agent failed to return valid structured JSON task list.",
                status_code=502
            )
            
        # 5. Persist tasks and assignments
        for item in extracted_response.tasks:
            # Format description to append Risks and Dependencies for ticket compatibility
            description = item.description
            if item.risks:
                description += f"\n\n**Risks Identified:**\n{item.risks}"
            if item.dependencies:
                deps_str = "\n".join([f"- {dep}" for dep in item.dependencies])
                description += f"\n\n**Dependencies:**\n{deps_str}"
                
            # Parse due date if present
            due_date_dt = None
            if item.due_date:
                try:
                    # Basic ISO format parser
                    from datetime import datetime
                    due_date_dt = datetime.fromisoformat(item.due_date.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Could not parse due date string: {item.due_date}")
                    due_date_dt = None
                    
            # Create Task DB Record
            new_task = Task(
                meeting_id=meeting.id,
                title=item.title,
                description=description,
                priority=item.priority.upper() if item.priority else "MEDIUM",
                status="Extracted",
                due_date=due_date_dt
            )
            db.add(new_task)
            db.flush()  # Populates new_task.id
            
            # Map assignee email to registered User profile
            if item.assignee_email:
                assignee_user = db.query(User).filter(User.email == item.assignee_email).first()
                if assignee_user:
                    assignment = TaskAssignment(
                        task_id=new_task.id,
                        user_id=assignee_user.id
                    )
                    db.add(assignment)
                    logger.info(f"Assigned task '{item.title}' to {item.assignee_email}")
                else:
                    logger.warning(f"Assignee email '{item.assignee_email}' does not match any registered User.")
                    
            created_tasks.append(new_task)
            
        # Update meeting status
        meeting.status = "Extracted"
        db.add(meeting)
        
        db.commit()
        logger.info(f"Successfully extracted and saved {len(created_tasks)} tasks for meeting {meeting_id}")
        
    return created_tasks
