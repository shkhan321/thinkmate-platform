import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Student


COURSE_PREFIXES = {"engineering": "ENG", "psychology": "PSY"}


def condition_for(sequence: str, task_number: int) -> str:
    if sequence == "A":
        return "thinkmate" if task_number == 1 else "worksheet"
    if sequence == "B":
        return "worksheet" if task_number == 1 else "thinkmate"
    raise ValueError("sequence must be A or B")


def assign_balanced_sequence(db: Session, course: str) -> str:
    """Minimisation-style randomisation. Assign the student to whichever
    crossover sequence currently has fewer members in the course, so the two
    arms stay balanced as students enrol. Ties are broken at random."""
    counts = dict(
        db.execute(
            select(Student.sequence, func.count())
            .where(Student.course == course)
            .group_by(Student.sequence)
        ).all()
    )
    a_count = int(counts.get("A", 0))
    b_count = int(counts.get("B", 0))
    if a_count < b_count:
        return "A"
    if b_count < a_count:
        return "B"
    return secrets.choice(["A", "B"])


def generate_study_id(db: Session, course: str) -> str:
    """Generate a unique, pseudonymous study ID such as ENG-7F3A2C8D1E.

    The random part is 5 bytes (40 bits). The student record can be looked up by
    this code via /api/auth/access-code with no login, so it must be infeasible
    to guess a valid code by enumeration — 3 bytes (24 bits) was brute-forceable.
    The code never encodes the crossover sequence."""
    prefix = COURSE_PREFIXES.get(course, course[:3].upper() or "STU")
    for _ in range(20):
        candidate = f"{prefix}-{secrets.token_hex(5).upper()}"
        if db.scalar(select(Student).where(Student.access_code == candidate)) is None:
            return candidate
    raise RuntimeError("Could not generate a unique study ID.")
