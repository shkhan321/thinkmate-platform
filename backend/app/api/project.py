from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import Student
from app.schemas import ProjectRequest, ProjectResponse
from app.services.consent import has_active_consent

router = APIRouter(prefix="/api/project", tags=["project"])

MAX_TITLE = 200
MAX_GOAL = 2000


def _require_consent(db: Session, student_id: str, consent_version: str) -> None:
    if not has_active_consent(db, student_id, consent_version):
        raise HTTPException(status_code=403, detail="Consent is required before saving project details.")


@router.post("", response_model=ProjectResponse)
def save_project(
    payload: ProjectRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """Capture the student's own capstone project and what they want to do.
    Every Socratic question is anchored to this, so ThinkMate works for any
    Mech/Aero or Psychology project, not a fixed scenario."""
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    _require_consent(db, student.id, settings.consent_version)

    title = " ".join(payload.project_title.split())
    goal = payload.project_goal.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Please tell us your project title.")
    if not goal:
        raise HTTPException(status_code=422, detail="Please tell us what you want to do.")

    student.project_title = title[:MAX_TITLE]
    student.project_goal = goal[:MAX_GOAL]
    db.commit()
    return ProjectResponse(
        student_id=student.id,
        project_title=student.project_title,
        project_goal=student.project_goal,
    )
