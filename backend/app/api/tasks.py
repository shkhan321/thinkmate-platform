from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_app_settings, get_db
from app.models import PilotSession, Student, Task, Turn, WorksheetResponse
from app.schemas import TaskListResponse, TaskResponse
from app.services.consent import has_active_consent
from app.services.routing import condition_for

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
def list_tasks(
    student_id: str = Query(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if not has_active_consent(db, student.id, settings.consent_version):
        raise HTTPException(status_code=403, detail="Consent is required before tasks are shown.")

    tasks = db.scalars(select(Task).where(Task.course == student.course).order_by(Task.task_number)).all()
    completed_task_ids = set(
        db.scalars(
            select(PilotSession.task_id).where(
                PilotSession.student_id == student.id,
                PilotSession.status == "complete",
            )
        ).all()
    )

    # A task is "in progress" if the student has a not-yet-complete session for it
    # that already holds some saved work (chat turns or worksheet answers).
    # Also track the latest session per task so the UI can review saved work.
    in_progress_task_ids: set[str] = set()
    latest_session_by_task: dict[str, str] = {}
    student_sessions = db.scalars(
        select(PilotSession)
        .where(PilotSession.student_id == student.id)
        .order_by(PilotSession.started_at)
    ).all()
    for student_session in student_sessions:
        latest_session_by_task[student_session.task_id] = student_session.id
        if student_session.status == "complete" or student_session.task_id in completed_task_ids:
            continue
        turn_count = db.scalar(
            select(func.count()).select_from(Turn).where(Turn.session_id == student_session.id)
        )
        response_count = db.scalar(
            select(func.count())
            .select_from(WorksheetResponse)
            .where(WorksheetResponse.session_id == student_session.id)
        )
        if (turn_count or 0) > 0 or (response_count or 0) > 0:
            in_progress_task_ids.add(student_session.task_id)

    return TaskListResponse(
        tasks=[
            TaskResponse(
                id=task.id,
                course=task.course,
                task_number=task.task_number,
                title=task.title,
                scenario=task.scenario,
                worksheet_steps=task.worksheet_steps,
                condition=condition_for(student.sequence, task.task_number),
                completed=task.id in completed_task_ids,
                in_progress=task.id in in_progress_task_ids,
                session_id=latest_session_by_task.get(task.id),
            )
            for task in tasks
        ]
    )
