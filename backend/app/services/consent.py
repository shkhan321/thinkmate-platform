from fastapi import HTTPException
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


def ensure_session_consent(db: Session, session, consent_version: str) -> None:
    """Stop an in-progress activity when the session's student has withdrawn or
    their consent version is stale. Without this, withdrawal only blocks the
    entry endpoints and a participant could keep reaching the model (and having
    data written/exported) after withdrawing — an ethics/protocol violation."""
    if not has_active_consent(db, session.student_id, consent_version):
        raise HTTPException(
            status_code=403,
            detail="This activity can't continue — consent has been withdrawn or needs renewing.",
        )


def has_withdrawn(db: Session, student_id: str) -> bool:
    """True when the student's most recent consent decision is a decline. Used to
    keep withdrawn participants out of the blinded scoring export."""
    latest = db.scalar(
        select(Consent).where(Consent.student_id == student_id).order_by(Consent.accepted_at.desc())
    )
    return latest is not None and not latest.accepted
