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


def move_for_tutor_turn(tutor_turn_count: int) -> dict:
    index = min(tutor_turn_count, len(SOCRATIC_MOVES) - 1)
    return SOCRATIC_MOVES[index]
