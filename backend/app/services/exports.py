import csv
import hashlib
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Feedback, PilotSession, Student, Task, Turn, WorksheetResponse


def _blinded_artifact_order(sessions: list[PilotSession]) -> list[PilotSession]:
    """Order sessions for blinded scoring by a stable hash of their id, NOT by
    start time or task number. This removes the positional tell: a rater cannot
    recover task order (and therefore condition) from an artifact's place in the
    list. The order is deterministic so repeated exports are reproducible."""
    return sorted(sessions, key=lambda session: hashlib.sha256(session.id.encode()).hexdigest())


def _artifact_key(index: int) -> str:
    """An independent per-ARTIFACT key (e.g. A0001). Crucially NOT per-student:
    a participant's two artifacts get two unrelated keys, so a rater cannot pair
    them (and thus cannot use one artifact's condition to infer the other's)."""
    return f"A{index + 1:04d}"


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
        # condition field). Each session becomes one independently-keyed artifact
        # in a hash-shuffled order, so raters cannot pair a participant's two
        # artifacts or recover task order from position. Empty (un-started)
        # sessions are dropped so the rater is never handed blank rows.
        # NOTE (residual, design-inherent): worksheet artifacts are a fixed set
        # of short answers and chat artifacts are free-form, so the two arms can
        # still differ in texture. Keying and ordering tells are removed here;
        # the texture difference is a property of the study design itself.
        artifacts = []
        for index, session in enumerate(_blinded_artifact_order(sessions_all)):
            reasoning = _session_reasoning(db, session)
            if not reasoning.strip():
                continue
            artifacts.append(
                {
                    "key": _artifact_key(index),
                    "course": courses.get(session.student_id),
                    "reasoning": reasoning,
                }
            )
        return {
            # Cohort composition only — one row per student with course, but NO
            # key, so it cannot be joined back to the keyed artifacts above.
            "students": [{"course": s.course} for s in students_all],
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
            "reasoning_state": turn.reasoning_state,
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
        # Normalized, condition-free rows for blinded scoring: independently
        # keyed per artifact and hash-shuffled so artifacts cannot be paired to a
        # participant or ordered by task/start time. Empty sessions are dropped.
        courses = {student.id: student.course for student in students_all}
        writer = csv.DictWriter(output, fieldnames=["artifact_key", "course", "reasoning"])
        writer.writeheader()
        for index, session in enumerate(_blinded_artifact_order(list(sessions))):
            reasoning = _session_reasoning(db, session)
            if not reasoning.strip():
                continue
            writer.writerow(
                {
                    "artifact_key": _artifact_key(index),
                    "course": courses.get(session.student_id, ""),
                    "reasoning": reasoning,
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
