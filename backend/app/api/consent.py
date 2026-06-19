from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import Consent, Student
from app.schemas import ConsentRequest, ConsentResponse

router = APIRouter(prefix="/api/consent", tags=["consent"])


@router.post("", response_model=ConsentResponse)
def record_consent(
    payload: ConsentRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    consent = Consent(
        student_id=student.id,
        accepted=payload.accepted,
        consent_version=settings.consent_version,
    )
    db.add(consent)
    db.commit()
    return ConsentResponse(accepted=payload.accepted, consent_version=settings.consent_version)
