from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import PilotSession, Task, WorksheetResponse
from app.schemas import WorksheetResponseRequest, WorksheetResponseResponse
from app.services.consent import ensure_session_consent

router = APIRouter(prefix="/api/worksheet", tags=["worksheet"])


@router.post("/response", response_model=WorksheetResponseResponse)
def worksheet_response(
    payload: WorksheetResponseRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    session = db.get(PilotSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    ensure_session_consent(db, session, settings.consent_version)
    if session.condition != "worksheet":
        raise HTTPException(status_code=400, detail="This session is assigned to ThinkMate dialogue.")
    if session.status == "complete":
        raise HTTPException(status_code=409, detail="This worksheet is already submitted.")

    # The task's step definitions are authoritative: an unknown step_key would
    # pollute the research export, and the stored prompt must be the prompt the
    # step actually shows — not whatever text a client chose to send.
    task = db.get(Task, session.task_id)
    steps_by_key = {step.get("key"): step for step in (task.worksheet_steps or [])} if task else {}
    step = steps_by_key.get(payload.step_key)
    if step is None:
        raise HTTPException(status_code=422, detail="Unknown worksheet step.")
    prompt_text = step.get("prompt") or payload.prompt

    # Upsert by (session, step) so resubmitting updates the answer instead of
    # appending a duplicate row.
    existing = db.scalar(
        select(WorksheetResponse).where(
            WorksheetResponse.session_id == session.id,
            WorksheetResponse.step_key == payload.step_key,
        )
    )
    if existing is not None:
        existing.prompt = prompt_text
        existing.response = payload.response
        db.commit()
        db.refresh(existing)
        return existing

    response = WorksheetResponse(
        session_id=session.id,
        step_key=payload.step_key,
        prompt=prompt_text,
        response=payload.response,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return response
