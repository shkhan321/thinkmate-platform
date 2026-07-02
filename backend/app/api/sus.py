from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import Student, SusResponse
from app.schemas import SusRequest, SusResponseModel
from app.services.consent import has_active_consent

router = APIRouter(prefix="/api/sus", tags=["sus"])


def sus_total(answers: list[int]) -> float:
    """Standard SUS scoring (Brooke, 1996): odd items score (answer - 1), even
    items score (5 - answer); the sum of the ten contributions × 2.5 gives the
    0-100 score. `answers` is q1..q10 in order."""
    odd = sum(answers[i] - 1 for i in range(0, 10, 2))
    even = sum(5 - answers[i] for i in range(1, 10, 2))
    return (odd + even) * 2.5


@router.post("", response_model=SusResponseModel)
def submit_sus(
    payload: SusRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """One System Usability Scale response per student (the pilot's promised
    usability metric, target mean >= 68). A re-submit updates the existing row —
    the client one-time gate is only a localStorage flag."""
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if not has_active_consent(db, student.id, settings.consent_version):
        raise HTTPException(status_code=403, detail="Consent is required before submitting the survey.")

    answers = [payload.q1, payload.q2, payload.q3, payload.q4, payload.q5,
               payload.q6, payload.q7, payload.q8, payload.q9, payload.q10]
    total = sus_total(answers)

    existing = db.scalar(select(SusResponse).where(SusResponse.student_id == student.id))
    if existing is not None:
        for index, value in enumerate(answers, start=1):
            setattr(existing, f"q{index}", value)
        existing.total = total
        db.commit()
        db.refresh(existing)
        return SusResponseModel(id=existing.id, total=existing.total)

    row = SusResponse(
        student_id=student.id,
        **{f"q{index}": value for index, value in enumerate(answers, start=1)},
        total=total,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return SusResponseModel(id=row.id, total=row.total)
