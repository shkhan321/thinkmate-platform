from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Consent, PilotSession, Student, Task
from app.schemas import CompleteSessionResponse, SessionResponse, StartSessionRequest
from app.services.routing import condition_for

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _ensure_consent(db: Session, student_id: str) -> None:
    consent = db.scalar(select(Consent).where(Consent.student_id == student_id, Consent.accepted.is_(True)))
    if consent is None:
        raise HTTPException(status_code=403, detail="Consent is required before starting a session.")


@router.post("", response_model=SessionResponse)
def start_session(payload: StartSessionRequest, db: Session = Depends(get_db)):
    student = db.get(Student, payload.student_id)
    task = db.get(Task, payload.task_id)
    if student is None or task is None:
        raise HTTPException(status_code=404, detail="Student or task not found.")
    if task.course != student.course:
        raise HTTPException(status_code=400, detail="Task does not belong to student's course.")
    _ensure_consent(db, student.id)

    session = PilotSession(
        student_id=student.id,
        task_id=task.id,
        condition=condition_for(student.sequence, task.task_number),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/complete", response_model=CompleteSessionResponse)
def complete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(PilotSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    session.status = "complete"
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    return CompleteSessionResponse(id=session.id, status=session.status)
