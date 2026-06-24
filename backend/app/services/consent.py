from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consent


def has_active_consent(db: Session, student_id: str, consent_version: str | None = None) -> bool:
    """Whether the student currently has valid, active consent.

    Uses the student's MOST RECENT consent decision, not "any acceptance ever":
    - a later decline (accepted=False) withdraws an earlier acceptance, so
      withdrawal is honored instead of silently ignored;
    - when ``consent_version`` is given, the latest acceptance must match it, so
      a mid-pilot change to the approved consent text forces re-consent rather
      than letting a participant continue under outdated terms.
    """
    latest = db.scalar(
        select(Consent)
        .where(Consent.student_id == student_id)
        .order_by(Consent.accepted_at.desc())
    )
    if latest is None or not latest.accepted:
        return False
    if consent_version is not None and latest.consent_version != consent_version:
        return False
    return True
