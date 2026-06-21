import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Feedback, PilotSession, Student, Task, Turn, WorksheetResponse


def _blinded_keys(students: list[Student]) -> dict[str, str]:
    """Stable per-student blinded key that is NOT the DB id or study ID, so
    raters cannot link an artifact back to a participant."""
    return {student.id: f"P{index + 1}" for index, student in enumerate(students)}


def _session_reasoning(db: Session, session: PilotSession) -> str:
    """The student's OWN reasoning for a session, condition-agnostic: their
    chat messages and/or worksheet answers plus their final answer, with no
    tutor text, move tags, role labels, or condition markers."""
    parts: list[str] = []
    for turn in db.scalars(
        select(Turn)
        .where(Turn.session_id == session.id, Turn.role == "student")
        .order_by(Turn.turn_number)
    ).all():
        parts.append(turn.content)
    for response in db.scalars(
        select(WorksheetResponse)
        .where(WorksheetResponse.session_id == session.id)
        .order_by(WorksheetResponse.created_at)
    ).all():
        parts.append(response.response)
    if session.final_answer:
        parts.append(session.final_answer)
    return "\n".join(part for part in parts if part and part.strip())


def build_json_export(db: Session, blinded: bool) -> dict:
    students_all = db.scalars(select(Student).order_by(Student.access_code)).all()
    sessions_all = db.scalars(select(PilotSession).order_by(PilotSession.started_at)).all()
    courses = {student.id: student.course for student in students_all}

    if blinded:
        # Blinded scoring export: only the student's reasoning, no identity and
        # nothing that reveals the condition (no tutor turns, move tags, or
        # condition field). One normalized artifact per session.
        keys = _blinded_keys(students_all)
        artifacts = [
            {
                "key": keys.get(session.student_id),
                "course": courses.get(session.student_id),
                "reasoning": _session_reasoning(db, session),
            }
            for session in sessions_all
        ]
        return {
            "students": [{"key": keys[s.id], "course": s.course} for s in students_all],
            "scoring_artifacts": artifacts,
            "feedback": [
                {"rating": item.rating, "comment": None}
                for item in db.scalars(select(Feedback).order_by(Feedback.created_at)).all()
            ],
        }

    # Full export for the research team's own analysis.
    students = [
        {
            "id": student.id,
            "course": student.course,
            "access_code": student.access_code,
            "display_name": student.display_name,
            "sequence": student.sequence,
            "project_title": student.project_title,
            "project_goal": student.project_goal,
        }
        for student in students_all
    ]
    sessions = [
        {
            "id": session.id,
            "student_id": session.student_id,
            "task_id": session.task_id,
            "status": session.status,
            "final_answer": session.final_answer,
            "condition": session.condition,
        }
        for session in sessions_all
    ]
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
    feedback = [
        {"id": item.id, "student_id": item.student_id, "rating": item.rating, "comment": item.comment}
        for item in db.scalars(select(Feedback).order_by(Feedback.created_at)).all()
    ]
    return {
        "students": students,
        "sessions": sessions,
        "turns": turns,
        "worksheet_responses": worksheet_responses,
        "feedback": feedback,
    }


def build_csv_export(db: Session, blinded: bool) -> str:
    output = io.StringIO()
    students_all = db.scalars(select(Student).order_by(Student.access_code)).all()
    sessions = db.scalars(select(PilotSession).order_by(PilotSession.started_at)).all()

    if blinded:
        # Normalized, condition-free rows for blinded scoring.
        keys = _blinded_keys(students_all)
        courses = {student.id: student.course for student in students_all}
        writer = csv.DictWriter(output, fieldnames=["student_key", "course", "reasoning"])
        writer.writeheader()
        for session in sessions:
            writer.writerow(
                {
                    "student_key": keys.get(session.student_id, ""),
                    "course": courses.get(session.student_id, ""),
                    "reasoning": _session_reasoning(db, session),
                }
            )
        return output.getvalue()

    fieldnames = [
        "student_id",
        "access_code",
        "display_name",
        "course",
        "sequence",
        "project_title",
        "project_goal",
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

    for session in sessions:
        student = db.get(Student, session.student_id)
        task = db.get(Task, session.task_id)
        base = {
            "student_id": session.student_id,
            "access_code": student.access_code,
            "display_name": student.display_name or "",
            "course": student.course,
            "sequence": student.sequence,
            "project_title": student.project_title or "",
            "project_goal": student.project_goal or "",
            "session_id": session.id,
            "task_number": task.task_number,
            "condition": session.condition,
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
        if session.final_answer:
            writer.writerow(base | {
                "record_type": "final_answer",
                "step_or_turn": "",
                "role": "student",
                "content": session.final_answer,
            })

    for item in db.scalars(select(Feedback).order_by(Feedback.created_at)).all():
        student = db.get(Student, item.student_id)
        writer.writerow({
            "student_id": item.student_id,
            "access_code": student.access_code if student else "",
            "display_name": (student.display_name or "") if student else "",
            "course": student.course if student else "",
            "sequence": student.sequence if student else "",
            "project_title": "",
            "project_goal": "",
            "session_id": "",
            "task_number": "",
            "condition": "",
            "status": "",
            "record_type": "feedback",
            "step_or_turn": str(item.rating),
            "role": "student",
            "content": item.comment or "",
        })
    return output.getvalue()
