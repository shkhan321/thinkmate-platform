from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Consent, Student, Task
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
            )
            for task in tasks
        ]
    )
