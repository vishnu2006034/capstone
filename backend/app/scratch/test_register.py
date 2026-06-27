import traceback
from app.core.database import SessionLocal
from app.models.models import User
from app.core.security import hash_password
from app.core.audit import log_audit_event

def run_direct_insert():
    db = SessionLocal()
    try:
        hashed_pwd = hash_password("password123")
        new_user = User(
            name="vishnu",
            email="vishnu@gmail.com",
            role="Employee",
            hashed_password=hashed_pwd
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print("Database Insert succeeded!")
        
        # Test audit log
        log_audit_event(db, "USER_REGISTER", {"email": new_user.email}, new_user.id)
        print("Audit logging succeeded!")
        
    except Exception as e:
        print("CRITICAL DIRECT INSERT FAILURE:")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_direct_insert()
