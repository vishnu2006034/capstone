import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.models import AuditLog

logger = logging.getLogger("app.core.audit")

def log_audit_event(
    db: Session,
    action: str,
    details: dict,
    user_id: Optional[UUID] = None
) -> AuditLog:
    """
    Persists a structured security audit trail log event to the database.
    Logs warnings to stderr if database commits fail.
    """
    try:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"[Audit Logged] Action: {action} | Actor: {user_id or 'System'}")
        return log_entry
    except Exception as e:
        logger.error(f"Failed to record audit event '{action}': {str(e)}")
        db.rollback()
        return None
