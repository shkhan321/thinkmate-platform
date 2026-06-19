from pydantic import BaseModel, ConfigDict


class AccessCodeRequest(BaseModel):
    access_code: str


class StartRequest(BaseModel):
    name: str
    course: str


class ProjectRequest(BaseModel):
    student_id: str
    project_title: str
    project_goal: str


class AccessCodeResponse(BaseModel):
    student_id: str
    access_code: str
    display_name: str | None = None
    course: str
    sequence: str
    project_title: str | None = None
    project_goal: str | None = None
    consent_accepted: bool
    returning: bool = False


class ProjectResponse(BaseModel):
    student_id: str
    project_title: str
    project_goal: str


class ConsentRequest(BaseModel):
    student_id: str
    accepted: bool


class ConsentResponse(BaseModel):
    accepted: bool
    consent_version: str


class TaskResponse(BaseModel):
    id: str
    course: str
    task_number: int
    title: str
    scenario: str
    worksheet_steps: list[dict]
    condition: str
    completed: bool = False


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


class StartSessionRequest(BaseModel):
    student_id: str
    task_id: str


class SessionResponse(BaseModel):
    id: str
    student_id: str
    task_id: str
    condition: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class CompleteSessionResponse(BaseModel):
    id: str
    status: str


class DialogueTurnRequest(BaseModel):
    session_id: str
    content: str


class TurnResponse(BaseModel):
    id: str
    session_id: str
    turn_number: int
    role: str
    content: str
    move_type: str | None = None
    paul_elder_target: str | None = None
    bloom_level: str | None = None
    safeguard_flag: bool

    model_config = ConfigDict(from_attributes=True)


class DialogueTurnResponse(BaseModel):
    student_turn: TurnResponse
    tutor_turn: TurnResponse


class WorksheetResponseRequest(BaseModel):
    session_id: str
    step_key: str
    prompt: str
    response: str


class WorksheetResponseResponse(BaseModel):
    id: str
    session_id: str
    step_key: str
    response: str

    model_config = ConfigDict(from_attributes=True)
