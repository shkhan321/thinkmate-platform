from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import PilotSession, Student, Task, Turn
from app.schemas import DialogueTurnRequest, DialogueTurnResponse, HintRequest, HintResponse
from app.services.consent import ensure_session_consent
from app.services.model_adapter import HINT_FALLBACK, generate_hint, generate_tutor_turn
from app.services.reasoning_state import assess_reasoning_state, select_move
from app.services.safeguard import apply_safeguard, flags_answer
from app.services.socratic import is_low_effort

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
    # Withdrawal/stale-consent must stop processing even mid-activity.
    ensure_session_consent(db, session, settings.consent_version)
    if session.condition != "thinkmate":
        raise HTTPException(status_code=400, detail="This session is assigned to guided worksheet.")
    if session.status == "complete":
        raise HTTPException(status_code=409, detail="This activity is already finished.")
    if not payload.content.strip():
        raise HTTPException(status_code=422, detail="Please write a message before sending.")
    task = db.get(Task, session.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    student = db.get(Student, session.student_id)

    # Build the conversation so far (before this message) so the tutor can build
    # on it and avoid repeating questions — this is what makes it feel like a
    # thinking partner with memory rather than a stateless prompt.
    prior_turns = db.scalars(
        select(Turn).where(Turn.session_id == session.id).order_by(Turn.turn_number)
    ).all()
    history = "\n".join(
        f"{'Student' if turn.role == 'student' else 'ThinkMate'}: {turn.content}" for turn in prior_turns[-6:]
    )

    student_turn = Turn(
        session_id=session.id,
        turn_number=_next_turn_number(db, session.id),
        role="student",
        content=payload.content,
        safeguard_flag=False,
    )
    db.add(student_turn)
    db.flush()

    # Reasoning-state engine: assess where the student's reasoning is weakest and
    # ask about THAT dimension, instead of walking a fixed move order. If they are
    # stuck, stay on the current point with an easier question. The assessment is
    # stored on the tutor turn as a per-turn reasoning trajectory for the research.
    project_title = (student.project_title or "") if student else ""
    project_goal = (student.project_goal or "") if student else ""
    moves_used = [turn.move_type for turn in prior_turns if turn.role == "tutor" and turn.move_type]
    stuck = is_low_effort(payload.content)
    # On a stuck turn we keep the previous move regardless of the assessment, so
    # skip the (paid) model call and store the cheap heuristic state instead.
    state = assess_reasoning_state(
        settings,
        project_title=project_title,
        project_goal=project_goal,
        history=history,
        student_content=payload.content,
        moves_used=moves_used,
        use_model=not (stuck and bool(moves_used)),
    )
    move = select_move(state, moves_used, stuck)
    raw_content = generate_tutor_turn(
        settings,
        task.title,
        task.scenario,
        payload.content,
        move,
        project_title=project_title,
        project_goal=project_goal,
        history=history,
        stuck=stuck,
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
        reasoning_state=state,
        safeguard_flag=safeguarded.flagged,
    )
    db.add(tutor_turn)
    try:
        db.commit()
    except IntegrityError:
        # Two turns raced for the same (session, turn_number) — the unique index
        # rejected the loser. Ask the student to wait for the in-flight reply
        # rather than silently corrupting the transcript order.
        db.rollback()
        raise HTTPException(status_code=409, detail="Please wait for the previous reply before sending again.")
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
    ensure_session_consent(db, session, settings.consent_version)
    # Research integrity: the guided-worksheet condition is the NON-AI control.
    # It must never reach the model, including via hints.
    if session.condition != "thinkmate":
        raise HTTPException(status_code=400, detail="Hints are only available in the ThinkMate discussion.")
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
    # A hint is a fill-in-the-blank frame, never an answer. If the model slips and
    # hands over a decision, fall back to the safe frame (the tutor turns are
    # guarded; hints must be too).
    if flags_answer(hint):
        hint = HINT_FALLBACK
    return HintResponse(hint=hint)
