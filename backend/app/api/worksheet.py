from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PilotSession, WorksheetResponse
from app.schemas import WorksheetResponseRequest, WorksheetResponseResponse

router = APIRouter(prefix="/api/worksheet", tags=["worksheet"])


@router.post("/response", response_model=WorksheetResponseResponse)
def worksheet_response(payload: WorksheetResponseRequest, db: Session = Depends(get_db)):
    session = db.get(PilotSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.condition != "worksheet":
        raise HTTPException(status_code=400, detail="This session is assigned to ThinkMate dialogue.")
    response = WorksheetResponse(
        session_id=session.id,
        step_key=payload.step_key,
        prompt=payload.prompt,
        response=payload.response,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return response
