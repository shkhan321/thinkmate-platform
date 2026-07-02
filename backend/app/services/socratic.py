SOCRATIC_MOVES = [
    {
        "move_type": "clarification",
        "paul_elder_target": "clarity",
        "bloom_level": "understand",
        "prompt": "What exactly is the claim you want to defend?",
    },
    {
        "move_type": "evidence_probe",
        "paul_elder_target": "accuracy",
        "bloom_level": "analyze",
        "prompt": "What evidence supports that claim, and how strong is it?",
    },
    {
        "move_type": "assumption_probe",
        "paul_elder_target": "depth",
        "bloom_level": "analyze",
        "prompt": "What assumption is hidden inside your reasoning?",
    },
    {
        "move_type": "counterview",
        "paul_elder_target": "breadth",
        "bloom_level": "evaluate",
        "prompt": "What would someone who disagrees with you say?",
    },
    {
        "move_type": "reflection",
        "paul_elder_target": "logic",
        "bloom_level": "create",
        "prompt": "How would you revise your answer after considering the evidence and counter-view?",
    },
]


_MOVES_BY_TYPE = {move["move_type"]: move for move in SOCRATIC_MOVES}


def move_by_type(move_type: str) -> dict:
    """The Socratic move with this move_type (falls back to the first move)."""
    return _MOVES_BY_TYPE.get(move_type, SOCRATIC_MOVES[0])


# Explicit "give me the answer / I give up" appeals. These signal low effort
# regardless of message length — a student writing a paragraph that ends in
# "just tell me the answer" is still asking to be handed it. Includes the
# common Arabic phrasings (UAEU students slip into Arabic naturally).
_GIVE_UP_PHRASES = (
    "just tell me",
    "tell me the answer",
    "give me the answer",
    "i give up",
    "أعطني الجواب",
    "اعطني الجواب",
    "قل لي الجواب",
    "ما هو الجواب",
)

# Generic "I'm stuck" signals. These only count as low effort when the WHOLE
# message is short — otherwise a substantive answer that merely contains the
# words (e.g. "this will help me decide between two materials") is wrongly
# flagged as stuck, which would stall the tutor on the same reasoning step.
# Includes common Arabic equivalents of "I don't know / help me".
_STUCK_PHRASES = (
    "i don't know",
    "i dont know",
    "idk",
    "dont know",
    "do not know",
    "not sure",
    "no idea",
    "no clue",
    "help me",
    "لا أعرف",
    "لا اعرف",
    "ما أدري",
    "ما ادري",
    "مش عارف",
    "ساعدني",
)
_SHORT_FILLERS = {"yes", "no", "ok", "okay", "maybe", "hmm", "sure", "nope", "yeah", "idk", "?", "help"}

# A "short" message for the purpose of the stuck-phrase check.
_STUCK_MAX_WORDS = 6


def is_give_up(content: str) -> bool:
    """True when the student is explicitly asking to be handed the answer
    ("just tell me the answer") rather than merely being stuck. Callers use
    this to pick a fallback that addresses the request head-on instead of a
    generic 'you're on the right track' line."""
    text = content.strip().lower()
    return bool(text) and any(phrase in text for phrase in _GIVE_UP_PHRASES)


def is_low_effort(content: str) -> bool:
    """True when the student's reply signals they are stuck or barely engaged."""
    text = content.strip().lower()
    if not text:
        return True
    if text in _SHORT_FILLERS:
        return True
    if is_give_up(text):
        return True
    words = text.split()
    if len(words) <= _STUCK_MAX_WORDS and any(phrase in text for phrase in _STUCK_PHRASES):
        return True
    # Very short and not a substantive answer (e.g. "no", "not really").
    return len(words) <= 2 and len(text) <= 8
