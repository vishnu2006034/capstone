from app.core.database import SessionLocal
from app.models.models import Transcript, Meeting

def check():
    db = SessionLocal()
    try:
        t = db.query(Transcript).order_by(Transcript.id.desc()).first()
        if t:
            meeting = db.query(Meeting).filter(Meeting.id == t.meeting_id).first()
            print(f"Latest Meeting: {meeting.title if meeting else 'Unknown'}")
            print("=== RAW TRANSCRIPT TEXT ===")
            print(t.raw_text)
            print("===========================")
        else:
            print("No transcripts found in database.")
    finally:
        db.close()

if __name__ == "__main__":
    check()
