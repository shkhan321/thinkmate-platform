from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import PilotSession, Student, Task, Turn
from app.schemas import DialogueTurnRequest, DialogueTurnResponse, HintRequest, HintResponse
from app.services.model_adapter import generate_hint, generate_tutor_turn
from app.services.safeguard import apply_safeguard
from app.services.socratic import move_for_tutor_turn

router = APIRouter(prefix="/api/dialogue", tags=["dialogue"])


def _next_turn_number(db: Session, session_id: str) -> int:
    current = db.scalar(select(func.max(Turn.turn_number)).where(Turn.session_id == session_id))
    return int(current or 0) + 1


@router.post("/turn", response_model=DialogueTurnResponse)
def dialogue_turn(
    payload: DialogueTurnRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    session = db.get(PilotSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.condition != "thinkmate":
        raise HTTPException(status_code=400, detail="This session is assigned to guided worksheet.")
    task = db.get(Task, session.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    student = db.get(Student, session.student_id)

    student_turn = Turn(
        session_id=session.id,
        turn_number=_next_turn_number(db, session.id),
        role="student",
        content=payload.content,
        safeguard_flag=False,
    )
    db.add(student_turn)
    db.flush()

    tutor_count = db.scalar(
        select(func.count()).select_from(Turn).where(Turn.session_id == session.id, Turn.role == "tutor")
    )
    move = move_for_tutor_turn(int(tutor_count or 0))
    raw_content = generate_tutor_turn(
        settings,
        task.title,
        task.scenario,
        payload.content,
        move,
        project_title=(student.project_title or "") if student else "",
        project_goal=(student.project_goal or "") if student else "",
    )
    safeguarded = apply_safeguard(raw_content)
    tutor_turn = Turn(
        session_id=session.id,
        turn_number=_next_turn_number(db, session.id),
        role="tutor",
        content=safeguarded.content,
        move_type=move["move_type"],
        paul_elder_target=move["paul_elder_target"],
        bloom_level=move["bloom_level"],
        safeguard_flag=safeguarded.flagged,
    )
    db.add(tutor_turn)
    db.commit()
    db.refresh(student_turn)
    db.refresh(tutor_turn)
    return DialogueTurnResponse(student_turn=student_turn, tutor_turn=tutor_turn)


@router.post("/hint", response_model=HintResponse)
def dialogue_hint(
    payload: HintRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """An optional, on-demand example reply for a stuck student. It models HOW
    to answer the current question, anchored to the student's project — a
    starter to adapt, never a finished answer."""
    session = db.get(PilotSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    student = db.get(Student, session.student_id)

    last_tutor = db.scalar(
        select(Turn)
        .where(Turn.session_id == session.id, Turn.role == "tutor")
        .order_by(Turn.turn_number.desc())
    )
    last_student = db.scalar(
        select(Turn)
        .where(Turn.session_id == session.id, Turn.role == "student")
        .order_by(Turn.turn_number.desc())
    )
    question = last_tutor.content if last_tutor else "What is your main claim about your project, and why?"

    hint = generate_hint(
        settings,
        question=question,
        project_title=(student.project_title or "") if student else "",
        project_goal=(student.project_goal or "") if student else "",
        last_student_message=last_student.content if last_student else "",
    )
    return HintResponse(hint=hint)
