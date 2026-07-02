import secrets
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import Feedback, HintEvent, PilotSession, Student, SusResponse, Turn, WorksheetResponse
from app.services.exports import build_csv_export, build_json_export
from app.services.model_adapter import audit_answer_leakage, has_chat_provider

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
        "hint_events": db.scalar(select(func.count()).select_from(HintEvent)) or 0,
        "sus_responses": db.scalar(select(func.count()).select_from(SusResponse)) or 0,
        "feedback": db.scalar(select(func.count()).select_from(Feedback)) or 0,
    }


@router.get("/leakage-audit", dependencies=[Depends(require_admin)])
def leakage_audit(
    n: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """LLM-judge fidelity audit over a random sample of tutor turns. Catches the
    SEMANTIC answer leaks the runtime blocklist cannot see (e.g. the answer
    embedded inside a question). Verdicts per turn: leak / steer / clean —
    intended for the pre-registered two-tier fidelity metric; results should be
    human-verified before reporting. Requires a configured chat model."""
    if not has_chat_provider(settings):
        raise HTTPException(
            status_code=503,
            detail="The leakage audit needs a configured chat model (Gemini or Poe key).",
        )
    sampled = db.scalars(
        select(Turn)
        .where(Turn.role == "tutor", Turn.safeguard_flag.is_(False))
        .order_by(func.random())
        .limit(n)
    ).all()
    results = []
    for turn in sampled:
        prior_student = db.scalar(
            select(Turn)
            .where(
                Turn.session_id == turn.session_id,
                Turn.role == "student",
                Turn.turn_number < turn.turn_number,
            )
            .order_by(Turn.turn_number.desc())
        )
        audit = audit_answer_leakage(settings, prior_student.content if prior_student else "", turn.content)
        results.append(
            {
                "turn_id": turn.id,
                "session_id": turn.session_id,
                "tutor_content": turn.content,
                "verdict": audit["verdict"] if audit else "unscored",
                "reason": audit["reason"] if audit else "judge unavailable or reply unusable",
            }
        )
    counts = Counter(result["verdict"] for result in results)
    scored = sum(count for verdict, count in counts.items() if verdict != "unscored")
    leaks = counts.get("leak", 0)
    return {
        "sampled": len(results),
        "counts": dict(counts),
        "leak_rate": round(leaks / scored, 3) if scored else None,
        "results": results,
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
