from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Consent, Student
from app.schemas import AccessCodeRequest, AccessCodeResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/access-code", response_model=AccessCodeResponse)
def access_code(payload: AccessCodeRequest, db: Session = Depends(get_db)):
    code = payload.access_code.strip().upper()
    student = db.scalar(select(Student).where(Student.access_code == code))
    if student is None:
        raise HTTPException(status_code=404, detail="Access code not found.")
    consent = db.scalar(
        select(Consent)
        .where(Consent.student_id == student.id, Consent.accepted.is_(True))
        .order_by(Consent.accepted_at.desc())
    )
    return AccessCodeResponse(
        student_id=student.id,
        access_code=student.access_code,
        course=student.course,
        sequence=student.sequence,
        consent_accepted=consent is not None,
    )
