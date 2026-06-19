def condition_for(sequence: str, task_number: int) -> str:
    if sequence == "A":
        return "thinkmate" if task_number == 1 else "worksheet"
    if sequence == "B":
        return "worksheet" if task_number == 1 else "thinkmate"
    raise ValueError("sequence must be A or B")
