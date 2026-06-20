from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Student, Task


SEED_STUDENTS = [
    {"access_code": "ENG-A-001", "course": "engineering", "sequence": "A"},
    {"access_code": "ENG-B-001", "course": "engineering", "sequence": "B"},
    {"access_code": "PSY-A-001", "course": "psychology", "sequence": "A"},
    {"access_code": "PSY-B-001", "course": "psychology", "sequence": "B"},
]


# Reasoning steps are written about the student's OWN capstone project, so the
# same matched activities work for any Mech/Aero or Psychology topic while
# staying comparable for blinded scoring across the crossover.
COMMON_STEPS = [
    {
        "key": "claim",
        "label": "Your claim",
        "prompt": "State your main claim or decision about your project.",
        "example": "e.g. “For my project I decided to … because it best meets my main goal.”",
    },
    {
        "key": "evidence",
        "label": "Your evidence",
        "prompt": "What evidence or reasons support it?",
        "example": "e.g. “The main reasons are …, and … backs this up.”",
    },
    {
        "key": "assumption",
        "label": "Your assumption",
        "prompt": "What assumption are you making that could be wrong?",
        "example": "e.g. “I am assuming that …. If that turned out wrong, then …”",
    },
    {
        "key": "counterview",
        "label": "A counter-view",
        "prompt": "What would a smart critic of your project say?",
        "example": "e.g. “Someone might argue that … because …”",
    },
    {
        "key": "reflection",
        "label": "Your reflection",
        "prompt": "After all this, what would you keep or change, and why?",
        "example": "e.g. “I would keep … but change … because …”",
    },
]


# Engineering and Psychology share the same two reasoning lenses; only the
# examples in the scenario text are tuned to the discipline. Both are anchored
# to "your project" so any capstone topic fits.
ENGINEERING_EXAMPLES = "a design choice, method, material, model, or analysis approach"
PSYCHOLOGY_EXAMPLES = "a research question, method, measure, sample, or interpretation"


def _activities(course: str, examples: str) -> list[dict]:
    return [
        {
            "course": course,
            "task_number": 1,
            "title": "Justify a key decision in your project",
            "scenario": (
                f"Pick one important decision in your capstone ({examples}) and build the case for "
                "why it is the right one."
            ),
            "worksheet_steps": COMMON_STEPS,
        },
        {
            "course": course,
            "task_number": 2,
            "title": "Stress-test your project",
            "scenario": (
                "Look hard at your own capstone for weak spots: the evidence behind it, the "
                "assumptions you are making, and a strong alternative you should consider."
            ),
            "worksheet_steps": COMMON_STEPS,
        },
    ]


SEED_TASKS = _activities("engineering", ENGINEERING_EXAMPLES) + _activities("psychology", PSYCHOLOGY_EXAMPLES)


def parse_pilot_access_codes(raw_codes: str) -> list[dict]:
    students = []
    for raw_entry in raw_codes.replace("\n", ";").split(";"):
        entry = raw_entry.strip()
        if not entry:
            continue
        parts = [part.strip() for part in entry.split(":")]
        if len(parts) != 3:
            raise ValueError("PILOT_ACCESS_CODES entries must use ACCESS_CODE:course:sequence format.")
        access_code, course, sequence = parts
        sequence = sequence.upper()
        if not access_code or not course or sequence not in {"A", "B"}:
            raise ValueError("PILOT_ACCESS_CODES entries need a code, course, and sequence A or B.")
        students.append({"access_code": access_code, "course": course.lower(), "sequence": sequence})
    return students


def seed_database(db: Session, pilot_students: list[dict] | None = None, include_demo_students: bool = True) -> None:
    student_rows = []
    if include_demo_students:
        student_rows.extend(SEED_STUDENTS)
    student_rows.extend(pilot_students or [])

    for student_data in student_rows:
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
        else:
            # Keep seeded task content in sync so existing databases pick up
            # updated activity wording without a manual migration.
            existing.title = task_data["title"]
            existing.scenario = task_data["scenario"]
            existing.worksheet_steps = task_data["worksheet_steps"]
    db.commit()
