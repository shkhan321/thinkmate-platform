from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import Feedback, Student
from app.schemas import FeedbackRequest, FeedbackResponse
from app.services.consent import has_active_consent

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

MAX_COMMENT = 1000


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """A simple end-of-session rating (1-5) plus an optional comment."""
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if not has_active_consent(db, student.id, settings.consent_version):
        raise HTTPException(status_code=403, detail="Consent is required before submitting feedback.")
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 5.")

    comment = (payload.comment or "").strip()[:MAX_COMMENT] or None
    feedback = Feedback(student_id=student.id, rating=payload.rating, comment=comment)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse(id=feedback.id, rating=feedback.rating)
