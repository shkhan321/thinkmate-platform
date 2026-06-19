from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Consent, Student
from app.schemas import AccessCodeRequest, AccessCodeResponse, StartRequest
from app.services.routing import (
    COURSE_PREFIXES,
    assign_balanced_sequence,
    generate_study_id,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_NAME_LENGTH = 80


def _normalise_name(raw_name: str) -> str:
    return " ".join(raw_name.split())


def _has_consent(db: Session, student_id: str) -> bool:
    consent = db.scalar(
        select(Consent)
        .where(Consent.student_id == student_id, Consent.accepted.is_(True))
        .order_by(Consent.accepted_at.desc())
    )
    return consent is not None


@router.post("/start", response_model=AccessCodeResponse)
def start(payload: StartRequest, db: Session = Depends(get_db)):
    """Student-friendly sign in: just a name and a course. The platform keeps
    a pseudonymous study ID for every student and assigns the crossover
    sequence with balanced randomisation. Returning students (same name and
    course) resume their existing study record."""
    name = _normalise_name(payload.name)
    course = payload.course.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="Please enter your name to continue.")
    if len(name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=422, detail="That name is too long.")
    if course not in COURSE_PREFIXES:
        raise HTTPException(status_code=422, detail="Please choose your course to continue.")

    existing = db.scalar(
        select(Student)
        .where(
            func.lower(Student.display_name) == name.lower(),
            Student.course == course,
        )
        .order_by(Student.created_at)
    )
    if existing is not None:
        return AccessCodeResponse(
            student_id=existing.id,
            access_code=existing.access_code,
            display_name=existing.display_name,
            course=existing.course,
            sequence=existing.sequence,
            consent_accepted=_has_consent(db, existing.id),
            returning=True,
        )

    student = Student(
        access_code=generate_study_id(db, course),
        display_name=name,
        course=course,
        sequence=assign_balanced_sequence(db, course),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return AccessCodeResponse(
        student_id=student.id,
        access_code=student.access_code,
        display_name=student.display_name,
        course=student.course,
        sequence=student.sequence,
        consent_accepted=False,
        returning=False,
    )


@router.post("/access-code", response_model=AccessCodeResponse)
def access_code(payload: AccessCodeRequest, db: Session = Depends(get_db)):
    code = payload.access_code.strip().upper()
    student = db.scalar(select(Student).where(Student.access_code == code))
    if student is None:
        raise HTTPException(status_code=404, detail="Access code not found.")
    return AccessCodeResponse(
        student_id=student.id,
        access_code=student.access_code,
        display_name=student.display_name,
        course=student.course,
        sequence=student.sequence,
        consent_accepted=_has_consent(db, student.id),
    )
