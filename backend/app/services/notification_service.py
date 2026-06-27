import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.models import User, Task, Notification, ComplianceReport
from app.core.config import settings

logger = logging.getLogger("app.services.notifications")

class NotificationService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> bool:
        """
        Sends an email using configured SMTP settings.
        Falls back to structured logging in development or sandbox environments.
        """
        logger.info(f"[Email Dispatch] Sending email to {to_email} | Subject: {subject}")
        
        # Check if SMTP details are configured
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning(f"[SMTP MOCK] Email would be sent to {to_email}. Host or user not configured.")
            logger.info(f"[SMTP MOCK Body]:\n{body}")
            return True
            
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
            server.close()
            logger.info(f"Successfully sent email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch email: {str(e)}")
            return False

    @staticmethod
    def send_dashboard_alert(user_id: UUID, title: str, content: str, db: Session) -> Notification:
        """
        Creates a new dashboard notification record in the database.
        """
        logger.info(f"[Dashboard Alert] Creating notification for User {user_id} | {title}")
        notify = Notification(
            user_id=user_id,
            title=title,
            content=content,
            is_read=False
        )
        db.add(notify)
        db.commit()
        db.refresh(notify)
        return notify

    @classmethod
    def send_daily_summary(cls, db: Session):
        """
        Gathers daily summaries of assigned tasks and compliance standings for each employee
        and emails them the brief report.
        """
        logger.info("Compiling daily summaries for all active users...")
        users = db.query(User).all()
        now = datetime.now(timezone.utc)
        
        for user in users:
            # Query incomplete tasks assigned to this user
            tasks = db.query(Task).join(Task.assignments).filter(
                Task.assignments.any(user_id=user.id),
                Task.status != "Done"
            ).all()
            
            if not tasks:
                continue
                
            body = f"Hello {user.name},\n\nHere is your daily action items summary:\n\n"
            for t in tasks:
                due_str = t.due_date.isoformat() if t.due_date else "No due date"
                body += f"- [{t.priority}] {t.title} | Status: {t.status} | Due: {due_str}\n"
                
            body += "\nEnsure tasks are resolved in line with SOP guidelines.\n\nBest,\nCompliance System"
            cls.send_email(user.email, "Daily Task & Compliance Summary", body)

    @classmethod
    def escalate_overdue_tasks(cls, db: Session):
        """
        Finds tasks that are past due by more than 24 hours. Escalates alerts
        to users with a 'Manager' or 'Admin' role.
        """
        logger.info("Scanning for overdue task escalations...")
        now = datetime.now(timezone.utc)
        escalation_threshold = now - timedelta(hours=24)
        
        # Query tasks due > 24 hours ago that are not Done
        overdue_tasks = db.query(Task).filter(
            Task.due_date < escalation_threshold,
            Task.status != "Done"
        ).all()
        
        if not overdue_tasks:
            logger.info("No overdue tasks warranting escalation found.")
            return

        # Fetch managers/admins to receive escalations
        managers = db.query(User).filter(User.role.in_(["Manager", "Admin"])).all()
        if not managers:
            logger.warning("No Manager/Admin registered in database to escalate to.")
            return

        for task in overdue_tasks:
            assignee_emails = ", ".join([a.assignee.email for a in task.assignments])
            subject = f"[ESCALATION] Task Overdue > 24 Hours: {task.title}"
            body = f"""
            The following task is severely overdue and has been escalated to leadership:
            
            - Title: {task.title}
            - Description: {task.description or 'No description'}
            - Due Date: {task.due_date}
            - Status: {task.status}
            - Assignees: {assignee_emails}
            
            Please follow up with the team.
            """
            
            for manager in managers:
                # 1. Send Email
                cls.send_email(manager.email, subject, body)
                # 2. Add Dashboard Alert
                cls.send_dashboard_alert(
                    user_id=manager.id,
                    title=f"ESCALATION: {task.title}",
                    content=f"Task assigned to [{assignee_emails}] is overdue by > 24h.",
                    db=db
                )
