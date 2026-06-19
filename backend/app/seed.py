from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Student, Task


SEED_STUDENTS = [
    {"access_code": "ENG-A-001", "course": "engineering", "sequence": "A"},
    {"access_code": "ENG-B-001", "course": "engineering", "sequence": "B"},
    {"access_code": "PSY-A-001", "course": "psychology", "sequence": "A"},
    {"access_code": "PSY-B-001", "course": "psychology", "sequence": "B"},
]


COMMON_STEPS = [
    {"key": "claim", "label": "Claim", "prompt": "State your main claim."},
    {"key": "evidence", "label": "Evidence", "prompt": "List the evidence that supports your claim."},
    {"key": "assumption", "label": "Assumption", "prompt": "Identify one assumption in your reasoning."},
    {"key": "counterview", "label": "Counter-view", "prompt": "Describe a plausible opposing view."},
    {"key": "reflection", "label": "Reflection", "prompt": "Revise or defend your claim after reflection."},
]


SEED_TASKS = [
    {
        "course": "engineering",
        "task_number": 1,
        "title": "Wing Design Trade-Off",
        "scenario": "A capstone team must choose between a lighter wing and a more robust wing under cost and safety constraints.",
        "worksheet_steps": COMMON_STEPS,
    },
    {
        "course": "engineering",
        "task_number": 2,
        "title": "Prototype Safety Decision",
        "scenario": "A prototype test shows borderline vibration behavior before a demonstration to stakeholders.",
        "worksheet_steps": COMMON_STEPS,
    },
    {
        "course": "psychology",
        "task_number": 1,
        "title": "Methodology Critique",
        "scenario": "A study claims that a phone-use intervention improves attention based on a small pre/post sample.",
        "worksheet_steps": COMMON_STEPS,
    },
    {
        "course": "psychology",
        "task_number": 2,
        "title": "Alternative Interpretation",
        "scenario": "A survey finds a link between confidence and exam performance, but the causal interpretation is unclear.",
        "worksheet_steps": COMMON_STEPS,
    },
]


def seed_database(db: Session) -> None:
    for student_data in SEED_STUDENTS:
        existing = db.scalar(select(Student).where(Student.access_code == student_data["access_code"]))
        if existing is None:
            db.add(Student(**student_data))

    for task_data in SEED_TASKS:
        existing = db.scalar(
            select(Task).where(
                Task.course == task_data["course"],
                Task.task_number == task_data["task_number"],
            )
        )
        if existing is None:
            db.add(Task(**task_data))
    db.commit()
