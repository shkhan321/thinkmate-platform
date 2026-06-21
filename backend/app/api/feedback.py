from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Consent, Feedback, Student
from app.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

MAX_COMMENT = 1000


@router.post("", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    """A simple end-of-session rating (1-5) plus an optional comment."""
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    consent = db.scalar(
        select(Consent).where(Consent.student_id == student.id, Consent.accepted.is_(True))
    )
    if consent is None:
        raise HTTPException(status_code=403, detail="Consent is required before submitting feedback.")
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 5.")

    comment = (payload.comment or "").strip()[:MAX_COMMENT] or None
    feedback = Feedback(student_id=student.id, rating=payload.rating, comment=comment)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse(id=feedback.id, rating=feedback.rating)
