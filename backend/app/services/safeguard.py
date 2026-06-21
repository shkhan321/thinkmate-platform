from dataclasses import dataclass


# Phrases that signal the tutor is giving an answer/solution rather than asking.
DIRECT_ANSWER_PATTERNS = (
    "the answer is",
    "the correct answer",
    "the right answer",
    "you should write",
    "you should use",
    "you should choose",
    "i recommend",
    "i suggest you",
    "i would recommend",
    "the solution is",
    "the best option is",
    "the best choice is",
    "the best approach is",
    "here is how",
    "here's how",
    "final answer",
    "in conclusion",
    "to summarize",
    "therefore the correct answer",
)

# A single Socratic question should be short. Anything much longer is likely an
# explanation/answer, so it is replaced with the safe fallback.
MAX_TUTOR_CHARS = 600

SAFE_FALLBACK = "I cannot give the answer directly. What evidence or assumption would you examine next?"


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
