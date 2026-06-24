"""Reasoning-state engine.

Instead of walking a fixed move order, the tutor first *assesses* the student's
reasoning across five dimensions, then asks about the WEAKEST one. This turns the
layer from a script into a model of the student's thinking — and records a
per-turn reasoning trajectory for the research, not just the final text.

Dimensions map one-to-one to the Socratic moves:
    claim       -> clarification
    evidence    -> evidence_probe
    assumptions -> assumption_probe
    counterview -> counterview
    validation  -> reflection
"""

from app.config import Settings
from app.services.model_adapter import generate_reasoning_assessment
from app.services.socratic import move_by_type

# (dimension, move_type) in pedagogical order. The order is the tie-breaker when
# several dimensions are equally weak: a vague claim is addressed before missing
# evidence, evidence before hidden assumptions, and so on.
DIMENSION_MOVES = [
    ("claim", "clarification"),
    ("evidence", "evidence_probe"),
    ("assumptions", "assumption_probe"),
    ("counterview", "counterview"),
    ("validation", "reflection"),
]

# Allowed levels per dimension, weakest first. The last value is "strong".
_LEVELS = {
    "claim": ["missing", "vague", "clear"],
    "evidence": ["missing", "weak", "strong"],
    "assumptions": ["hidden", "surfaced"],
    "counterview": ["ignored", "engaged"],
    "validation": ["absent", "present"],
}


def _weak_level(dimension: str) -> str:
    return _LEVELS[dimension][0]


def _strong_level(dimension: str) -> str:
    return _LEVELS[dimension][-1]


def is_strong(dimension: str, level) -> bool:
    """A dimension counts as covered only at its strongest level."""
    return level == _strong_level(dimension)


def _heuristic_state(moves_used: list[str]) -> dict:
    """No-model fallback (demo/offline). A dimension is treated as covered once
    its move has already been used, which reproduces the original ordered walk
    so behaviour is predictable without a model."""
    used = set(moves_used)
    dimensions = {
        dimension: (_strong_level(dimension) if move_type in used else _weak_level(dimension))
        for dimension, move_type in DIMENSION_MOVES
    }
    return {"dimensions": dimensions, "source": "heuristic"}


def _normalize(raw: dict) -> dict:
    """Coerce a model assessment into known dimensions/levels. Any unknown or
    missing value defaults to the weakest level, so a sloppy model response can
    never mark a dimension 'done' by accident."""
    # Accept both the nested {"dimensions": {...}} shape and the flat {...} shape
    # the prompt actually asks for; only treat "dimensions" as the source when it
    # is genuinely a dict (otherwise the flat keys would be lost).
    if isinstance(raw, dict) and isinstance(raw.get("dimensions"), dict):
        raw_dims = raw["dimensions"]
    elif isinstance(raw, dict):
        raw_dims = raw
    else:
        raw_dims = {}
    dimensions = {}
    for dimension, _move in DIMENSION_MOVES:
        value = raw_dims.get(dimension) if isinstance(raw_dims, dict) else None
        if isinstance(value, str) and value.lower() in _LEVELS[dimension]:
            dimensions[dimension] = value.lower()
        else:
            dimensions[dimension] = _weak_level(dimension)
    return {"dimensions": dimensions, "source": "model"}


def assess_reasoning_state(
    settings: Settings,
    project_title: str,
    project_goal: str,
    history: str,
    student_content: str,
    moves_used: list[str],
    use_model: bool = True,
) -> dict:
    """Assess the student's reasoning. Uses the model when configured and
    use_model is True; otherwise (and on any model/parse failure) falls back to
    the deterministic heuristic. Callers pass use_model=False when the result
    will be discarded anyway (e.g. a stuck turn that stays on the same move), to
    avoid a wasted model call."""
    if use_model:
        raw = generate_reasoning_assessment(
            settings,
            project_title=project_title,
            project_goal=project_goal,
            history=history,
            student_content=student_content,
        )
        if raw:
            return _normalize(raw)
    return _heuristic_state(moves_used)


def select_move(state: dict, moves_used: list[str], stuck: bool) -> dict:
    """Pick the next Socratic move.

    Target the weakest dimension the tutor has NOT already asked about. This keeps
    the adaptivity (a dimension the student already nailed is skipped) while
    guaranteeing forward progress: each move is asked at most once before the
    tutor closes on reflection, so a still-weak dimension can never trap the tutor
    on one move turn after turn. If the student is stuck, stay on the current
    point with an easier question instead of advancing."""
    if stuck and moves_used:
        return move_by_type(moves_used[-1])
    dimensions = state.get("dimensions", {})
    used = set(moves_used)
    for dimension, move_type in DIMENSION_MOVES:
        if move_type not in used and not is_strong(dimension, dimensions.get(dimension)):
            return move_by_type(move_type)
    # Every weak dimension has already been raised (or all are strong) — close on
    # reflection rather than re-asking the same question.
    return move_by_type("reflection")
