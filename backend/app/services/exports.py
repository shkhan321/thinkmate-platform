import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PilotSession, Student, Task, Turn, WorksheetResponse


def build_json_export(db: Session, blinded: bool) -> dict:
    students = []
    for student in db.scalars(select(Student).order_by(Student.access_code)).all():
        item = {"id": student.id, "course": student.course}
        if not blinded:
            item["access_code"] = student.access_code
            item["display_name"] = student.display_name
            item["sequence"] = student.sequence
        students.append(item)

    sessions = []
    for session in db.scalars(select(PilotSession).order_by(PilotSession.started_at)).all():
        item = {
            "id": session.id,
            "student_id": session.student_id,
            "task_id": session.task_id,
            "status": session.status,
        }
        if not blinded:
            item["condition"] = session.condition
        sessions.append(item)

    turns = [
        {
            "id": turn.id,
            "session_id": turn.session_id,
            "turn_number": turn.turn_number,
            "role": turn.role,
            "content": turn.content,
            "move_type": turn.move_type,
            "paul_elder_target": turn.paul_elder_target,
            "bloom_level": turn.bloom_level,
            "safeguard_flag": turn.safeguard_flag,
        }
        for turn in db.scalars(select(Turn).order_by(Turn.session_id, Turn.turn_number)).all()
    ]

    worksheet_responses = [
        {
            "id": response.id,
            "session_id": response.session_id,
            "step_key": response.step_key,
            "prompt": response.prompt,
            "response": response.response,
        }
        for response in db.scalars(select(WorksheetResponse).order_by(WorksheetResponse.created_at)).all()
    ]
    return {
        "students": students,
        "sessions": sessions,
        "turns": turns,
        "worksheet_responses": worksheet_responses,
    }


def build_csv_export(db: Session, blinded: bool) -> str:
    output = io.StringIO()
    fieldnames = [
        "student_id",
        "access_code",
        "display_name",
        "course",
        "sequence",
        "session_id",
        "task_number",
        "condition",
        "status",
        "record_type",
        "step_or_turn",
        "role",
        "content",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    sessions = db.scalars(select(PilotSession).order_by(PilotSession.started_at)).all()
    for session in sessions:
        student = db.get(Student, session.student_id)
        task = db.get(Task, session.task_id)
        base = {
            "student_id": session.student_id,
            "access_code": "" if blinded else student.access_code,
            "display_name": "" if blinded else (student.display_name or ""),
            "course": student.course,
            "sequence": "" if blinded else student.sequence,
            "session_id": session.id,
            "task_number": task.task_number,
            "condition": "" if blinded else session.condition,
            "status": session.status,
        }
        for turn in db.scalars(select(Turn).where(Turn.session_id == session.id).order_by(Turn.turn_number)).all():
            writer.writerow(base | {
                "record_type": "turn",
                "step_or_turn": str(turn.turn_number),
                "role": turn.role,
                "content": turn.content,
            })
        for response in db.scalars(select(WorksheetResponse).where(WorksheetResponse.session_id == session.id)).all():
            writer.writerow(base | {
                "record_type": "worksheet",
                "step_or_turn": response.step_key,
                "role": "student",
                "content": response.response,
            })
    return output.getvalue()
