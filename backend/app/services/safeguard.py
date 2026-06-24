from dataclasses import dataclass


# ThinkMate is now allowed to encourage, reassure and gently STEER the student in
# the right direction (a little answer-direction is fine — that is what keeps them
# from feeling lost). So the safeguard only catches a FLAT answer-dump where the
# tutor hands over the finished conclusion, not directional encouragement like
# "you could look at…" or "I'd consider…".
DIRECT_ANSWER_PATTERNS = (
    "the answer is",
    "the correct answer",
    "the right answer",
    "the final answer",
    "therefore the correct answer",
    "the solution is",
    "here is the answer",
    "here's the answer",
    "the answer to your question is",
)

# A warm reply (a brief acknowledgement plus one question) is still short. Anything
# much longer is likely an explanation/answer dump, so it is replaced.
MAX_TUTOR_CHARS = 800

SAFE_FALLBACK = (
    "You're on the right track — let's keep this one yours. "
    "What evidence or assumption would you look at next?"
)


@dataclass(frozen=True)
class SafeguardResult:
    content: str
    flagged: bool


def apply_safeguard(content: str) -> SafeguardResult:
    lowered = content.lower()
    flagged = any(pattern in lowered for pattern in DIRECT_ANSWER_PATTERNS)
    if not flagged and len(content) > MAX_TUTOR_CHARS:
        # Overly long replies tend to explain rather than ask one question.
        flagged = True
    if flagged:
        return SafeguardResult(content=SAFE_FALLBACK, flagged=True)
    if "?" not in content:
        return SafeguardResult(content=f"{content.rstrip()} What reasoning supports that?", flagged=False)
    return SafeguardResult(content=content, flagged=False)
