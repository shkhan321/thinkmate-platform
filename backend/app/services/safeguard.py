from dataclasses import dataclass


# ThinkMate may encourage, reassure and gently STEER ("you could look at…",
# "I'd consider…") — a little direction keeps students from feeling lost. But it
# must not HAND OVER the choice. So we still block a flat answer-dump AND a flat
# recommendation that names the decision for the student. Soft, exploratory
# phrasing is intentionally NOT matched here.
DIRECT_ANSWER_PATTERNS = (
    # Flat answer / solution dumps
    "the answer is",
    "the correct answer",
    "the right answer",
    "the final answer",
    "therefore the correct answer",
    "the solution is",
    "here is the answer",
    "here's the answer",
    "the answer to your question is",
    # Flat recommendations (handing the choice instead of steering toward it)
    "the best option is",
    "the best choice is",
    "the best approach is",
    "the best material is",
    "the correct choice is",
    "the right choice is",
    "the correct option is",
    "the right option is",
    "the correct material",
    "the right material",
    "you should choose",
    "you should use",
    "you should select",
    "you should pick",
    "you should go with",
    "i recommend",
    "i'd recommend",
    "i would recommend",
    "my recommendation",
    "i'd go with",
    "i would go with",
    "go with the",
    "opt for",
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


def flags_answer(content: str) -> bool:
    """True when the text hands over the answer/choice (a flat answer-dump or a
    flat recommendation) or is long enough to be an explanation dump. Shared by
    the tutor-turn safeguard and the hint guard."""
    lowered = content.lower()
    if any(pattern in lowered for pattern in DIRECT_ANSWER_PATTERNS):
        return True
    return len(content) > MAX_TUTOR_CHARS


def apply_safeguard(content: str) -> SafeguardResult:
    if flags_answer(content):
        return SafeguardResult(content=SAFE_FALLBACK, flagged=True)
    if "?" not in content:
        return SafeguardResult(content=f"{content.rstrip()} What reasoning supports that?", flagged=False)
    return SafeguardResult(content=content, flagged=False)
