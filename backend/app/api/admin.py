import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import PilotSession, Student, Turn, WorksheetResponse
from app.services.exports import build_csv_export, build_json_export

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(
    request: Request,
    x_admin_password: Annotated[str | None, Header(alias="X-Admin-Password")] = None,
    settings: Settings = Depends(get_app_settings),
) -> None:
    # Rate-limit attempts per client BEFORE checking the password, so the single
    # static admin password cannot be brute forced quickly.
    limiter = getattr(request.app.state, "admin_rate_limiter", None)
    if limiter is not None:
        client = request.client.host if request.client else "unknown"
        limiter.hit(f"admin:{client}")
    if not x_admin_password or not secrets.compare_digest(x_admin_password, settings.admin_password):
        raise HTTPException(status_code=401, detail="Invalid admin password.")


@router.get("/summary", dependencies=[Depends(require_admin)])
def summary(db: Session = Depends(get_db)):
    return {
        "students": db.scalar(select(func.count()).select_from(Student)) or 0,
        "sessions": db.scalar(select(func.count()).select_from(PilotSession)) or 0,
        "turns": db.scalar(select(func.count()).select_from(Turn)) or 0,
        "worksheet_responses": db.scalar(select(func.count()).select_from(WorksheetResponse)) or 0,
    }


@router.get("/export", dependencies=[Depends(require_admin)])
def export_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    blinded: bool = Query(False),
    db: Session = Depends(get_db),
):
    if format == "csv":
        return PlainTextResponse(build_csv_export(db, blinded), media_type="text/csv")
    return build_json_export(db, blinded)
