from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Consent, PilotSession, Student, Task, Turn, WorksheetResponse
from app.schemas import TaskListResponse, TaskResponse
from app.services.routing import condition_for

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _has_consent(db: Session, student_id: str) -> bool:
    return db.scalar(select(Consent).where(Consent.student_id == student_id, Consent.accepted.is_(True))) is not None


@router.get("", response_model=TaskListResponse)
def list_tasks(student_id: str = Query(...), db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if not _has_consent(db, student.id):
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
    in_progress_task_ids: set[str] = set()
    open_sessions = db.scalars(
        select(PilotSession).where(
            PilotSession.student_id == student.id,
            PilotSession.status != "complete",
        )
    ).all()
    for open_session in open_sessions:
        if open_session.task_id in completed_task_ids:
            continue
        turn_count = db.scalar(
            select(func.count()).select_from(Turn).where(Turn.session_id == open_session.id)
        )
        response_count = db.scalar(
            select(func.count())
            .select_from(WorksheetResponse)
            .where(WorksheetResponse.session_id == open_session.id)
        )
        if (turn_count or 0) > 0 or (response_count or 0) > 0:
            in_progress_task_ids.add(open_session.task_id)

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
            )
            for task in tasks
        ]
    )
