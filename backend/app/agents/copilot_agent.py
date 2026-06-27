import logging
from sqlalchemy.orm import Session
import sqlalchemy as sa
from datetime import datetime, timezone

from google.antigravity import Agent, LocalAgentConfig
from app.models.models import Task, User, TaskAssignment, Meeting, ComplianceReport
from app.core.exceptions import AppException

logger = logging.getLogger("app.agents.copilot")


async def ask_manager_copilot(query: str, db: Session) -> str:
    """
    Assembles database metrics (overdue task items, user workloads, meeting stats, compliance breaches)
    and feeds them to the Google ADK Agent to formulate natural language answers.
    """
    logger.info(f"Manager Copilot processing query: {query}")
    now = datetime.now(timezone.utc)

    # 1. Gather Overdue Tasks Context
    overdue = db.query(Task).filter(
        Task.due_date < now,
        Task.status != "Done"
    ).all()
    overdue_context = ""
    for t in overdue:
        assignees = ", ".join([a.assignee.email for a in t.assignments])
        overdue_context += f"- Task: '{t.title}' | Due: {t.due_date.isoformat()} | Assignees: {assignees}\n"
    if not overdue_context:
        overdue_context = "No overdue tasks currently.\n"

    # 2. Gather User Workloads Context (Incomplete tasks count per employee)
    workload = db.query(
        User.name,
        User.email,
        sa.func.count(Task.id)
    ).join(TaskAssignment, TaskAssignment.user_id == User.id)\
     .join(Task, Task.id == TaskAssignment.task_id)\
     .filter(Task.status != "Done")\
     .group_by(User.name, User.email).all()
    
    workload_context = ""
    for name, email, count in workload:
        workload_context += f"- User: {name} ({email}) | Incomplete Tasks: {count}\n"
    if not workload_context:
        workload_context = "No active task assignments found.\n"

    # 3. Gather Meetings Creating the Most Work Context (Tasks count grouped by Meeting)
    meeting_stats = db.query(
        Meeting.title,
        sa.func.count(Task.id)
    ).join(Task, Task.meeting_id == Meeting.id)\
     .group_by(Meeting.title)\
     .order_by(sa.func.count(Task.id).desc()).all()
    
    meeting_context = ""
    for title, count in meeting_stats:
        meeting_context += f"- Meeting: '{title}' | Tasks Created: {count}\n"
    if not meeting_context:
        meeting_context = "No tasks generated from meetings.\n"

    # 4. Gather SOP Compliance Breaches Context (Failed compliance reviews and reasoning)
    violations = db.query(Task.title, ComplianceReport.reasoning_trace, ComplianceReport.risk_level)\
                   .join(ComplianceReport, ComplianceReport.task_id == Task.id)\
                   .filter(ComplianceReport.status == "FAILED").all()
    
    violations_context = ""
    for task_title, reasoning, risk in violations:
        # Extract first 150 chars of reasoning to keep context window clean
        short_reason = reasoning[:150] + "..." if reasoning and len(reasoning) > 150 else reasoning
        violations_context += f"- Task: '{task_title}' | Risk Level: {risk} | Breach Reason: {short_reason}\n"
    if not violations_context:
        violations_context = "No compliance violations recorded.\n"

    # 5. Formulate Prompt
    prompt = f"""
    You are the Manager Copilot Agent. Your role is to interpret leadership queries and provide
    clear, concise, natural-language insights using real-time database contexts.
    
    USER QUERY:
    "{query}"
    
    DATABASE CONTEXT:
    
    === Overdue Tasks ===
    {overdue_context}
    
    === User Workloads ===
    {workload_context}
    
    === Meeting Task Distributions ===
    {meeting_context}
    
    === SOP Compliance Violations ===
    {violations_context}
    
    INSTRUCTIONS:
    - Answer the USER QUERY directly using ONLY the provided DATABASE CONTEXT.
    - If the user asks 'What is overdue?', summarize overdue items, deadlines, and assignees.
    - If the user asks 'Who is overloaded?', identify users with high workloads.
    - If the user asks 'What meetings created the most work?', rank meetings by task count.
    - If the user asks 'Which SOPs are frequently violated?', analyze the violation reasons and name the policies breached.
    - Be professional, conversational, and format lists using clean Markdown bullet points.
    - Do not invent details not present in the context.
    """

    # 6. Invoke Google ADK Agent
    config = LocalAgentConfig()
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        answer = await response.text()
        return answer
