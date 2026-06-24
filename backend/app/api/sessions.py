from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import PilotSession, Student, Task, Turn, WorksheetResponse
from app.services.consent import has_active_consent
from app.schemas import (
    AnswerRequest,
    AnswerResponse,
    CompleteSessionResponse,
    SessionResponse,
    SessionStateResponse,
    SessionSummaryResponse,
    StartSessionRequest,
)
from app.services.model_adapter import generate_session_summary
from app.services.routing import condition_for

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _ensure_consent(db: Session, student_id: str, consent_version: str) -> None:
    if not has_active_consent(db, student_id, consent_version):
        raise HTTPException(status_code=403, detail="Consent is required before starting a session.")


def student_transcript(turns: list[Turn], final_answer: str | None) -> str:
    """The student's OWN words only (tutor turns excluded), so the AI thinking
    brief reflects the student's reasoning and never ThinkMate's phrasing. This
    is blinding-relevant: tutor text must not bleed into a scored artifact."""
    transcript = "\n".join(f"S: {turn.content}" for turn in turns if turn.role == "student")
    if final_answer:
        transcript += f"\nS (final answer): {final_answer}"
    return transcript


@router.post("", response_model=SessionResponse)
def start_session(
    payload: StartSessionRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    student = db.get(Student, payload.student_id)
    task = db.get(Task, payload.task_id)
    if student is None or task is None:
        raise HTTPException(status_code=404, detail="Student or task not found.")
    if task.course != student.course:
        raise HTTPException(status_code=400, detail="Task does not belong to student's course.")
    _ensure_consent(db, student.id, settings.consent_version)

    # Reuse the student's existing session for this task so their work is never
    # lost on navigation and we keep one canonical record per task (no duplicates).
    existing = db.scalar(
        select(PilotSession)
        .where(PilotSession.student_id == student.id, PilotSession.task_id == task.id)
        .order_by(PilotSession.started_at.desc())
    )
    if existing is not None:
        return existing

    session = PilotSession(
        student_id=student.id,
        task_id=task.id,
        condition=condition_for(student.sequence, task.task_number),
    )
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        # Lost a concurrent create race (double-click / two tabs). The unique
        # (student_id, task_id) index rejected the duplicate; return the session
        # the winning request created so the student keeps one canonical record.
        db.rollback()
        existing = db.scalar(
            select(PilotSession)
            .where(PilotSession.student_id == student.id, PilotSession.task_id == task.id)
            .order_by(PilotSession.started_at.desc())
        )
        if existing is not None:
            return existing
        raise
    db.refresh(session)
    return session


@router.post("/{session_id}/complete", response_model=CompleteSessionResponse)
def complete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(PilotSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    # Idempotent: completing an already-complete session must not overwrite the
    # original completion timestamp (that would corrupt any timing analysis).
    if session.status != "complete":
        session.status = "complete"
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
    return CompleteSessionResponse(id=session.id, status=session.status)


@router.get("/{session_id}/state", response_model=SessionStateResponse)
def session_state(session_id: str, db: Session = Depends(get_db)):
    """Return a session's saved content so the student can resume exactly where
    they left off — the chat transcript and any worksheet answers."""
    session = db.get(PilotSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    turns = db.scalars(
        select(Turn).where(Turn.session_id == session.id).order_by(Turn.turn_number)
    ).all()
    rows = db.scalars(
        select(WorksheetResponse)
        .where(WorksheetResponse.session_id == session.id)
        .order_by(WorksheetResponse.created_at)
    ).all()
    return SessionStateResponse(
        condition=session.condition,
        status=session.status,
        final_answer=session.final_answer,
        turns=list(turns),
        worksheet_responses=list(rows),
    )


@router.post("/{session_id}/answer", response_model=AnswerResponse)
def save_final_answer(session_id: str, payload: AnswerRequest, db: Session = Depends(get_db)):
    """Store the student's own improved answer at the end of a ThinkMate
    dialogue. This is the point of the tool — the student articulates the
    conclusion themselves, and it becomes a clean reasoning artifact for
    scoring."""
    session = db.get(PilotSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status == "complete":
        raise HTTPException(status_code=409, detail="This activity is already finished.")
    answer = payload.answer.strip()
    if not answer:
        raise HTTPException(status_code=422, detail="Please write your answer, or skip this step.")
    session.final_answer = answer
    db.commit()
    return AnswerResponse(id=session.id, final_answer=session.final_answer)


@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
def session_summary(
    session_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """A takeaway the student can keep and reuse in their capstone. For a
    ThinkMate dialogue it is an AI brief of the student's OWN reasoning. For the
    worksheet it is a plain, non-AI recap of their answers — this keeps the
    non-AI control condition uncontaminated."""
    session = db.get(PilotSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    student = db.get(Student, session.student_id)

    if session.condition == "worksheet":
        rows = db.scalars(
            select(WorksheetResponse)
            .where(WorksheetResponse.session_id == session.id)
            .order_by(WorksheetResponse.created_at)
        ).all()
        if not rows:
            return SessionSummaryResponse(kind="plain", summary="You have not saved any answers for this worksheet yet.")
        recap = "\n\n".join(f"{row.prompt}\n{row.response}" for row in rows)
        return SessionSummaryResponse(kind="plain", summary=recap, final_answer=session.final_answer)

    turns = db.scalars(
        select(Turn).where(Turn.session_id == session.id).order_by(Turn.turn_number)
    ).all()
    transcript = student_transcript(turns, session.final_answer)
    summary = generate_session_summary(
        settings,
        project_title=(student.project_title or "") if student else "",
        project_goal=(student.project_goal or "") if student else "",
        transcript=transcript,
    )
    return SessionSummaryResponse(kind="ai", summary=summary, final_answer=session.final_answer)
