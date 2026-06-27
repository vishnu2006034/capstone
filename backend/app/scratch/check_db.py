import sys
from app.core.database import SessionLocal
from app.models.models import User

def check():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total users in database: {len(users)}")
        for u in users:
            print(f"- ID: {u.id} | Name: {u.name} | Email: {u.email} | Role: {u.role}")
    except Exception as e:
        print(f"Error checking database: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
