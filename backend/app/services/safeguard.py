from dataclasses import dataclass


DIRECT_ANSWER_PATTERNS = (
    "the answer is",
    "you should write",
    "final answer",
    "in conclusion",
    "therefore the correct answer",
)

SAFE_FALLBACK = "I cannot give the answer directly. What evidence or assumption would you examine next?"


@dataclass(frozen=True)
class SafeguardResult:
    content: str
    flagged: bool


def apply_safeguard(content: str) -> SafeguardResult:
    lowered = content.lower()
    flagged = any(pattern in lowered for pattern in DIRECT_ANSWER_PATTERNS)
    if flagged:
        return SafeguardResult(content=SAFE_FALLBACK, flagged=True)
    if "?" not in content:
        return SafeguardResult(content=f"{content.rstrip()} What reasoning supports that?", flagged=False)
    return SafeguardResult(content=content, flagged=False)
