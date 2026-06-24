from pydantic import BaseModel, ConfigDict, Field

# Outer caps on free text reaching the database and the paid model. These are
# generous (well above any genuine student answer) and exist only to stop a
# single unauthenticated request from storing megabytes or running up model
# cost. Endpoints may trim further; these reject the absurd before that.
ID_MAX = 64
SHORT_TEXT_MAX = 1000
LONG_TEXT_MAX = 6000


class AccessCodeRequest(BaseModel):
    access_code: str = Field(max_length=ID_MAX)


class StartRequest(BaseModel):
    name: str = Field(max_length=120)
    course: str = Field(max_length=40)


class ProjectRequest(BaseModel):
    student_id: str = Field(max_length=ID_MAX)
    project_title: str = Field(max_length=400)
    project_goal: str = Field(max_length=LONG_TEXT_MAX)


class AccessCodeResponse(BaseModel):
    student_id: str
    access_code: str
    display_name: str | None = None
    course: str
    project_title: str | None = None
    project_goal: str | None = None
    consent_accepted: bool
    returning: bool = False


class ProjectResponse(BaseModel):
    student_id: str
    project_title: str
    project_goal: str


class ConsentRequest(BaseModel):
    student_id: str = Field(max_length=ID_MAX)
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
    in_progress: bool = False
    session_id: str | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


class StartSessionRequest(BaseModel):
    student_id: str = Field(max_length=ID_MAX)
    task_id: str = Field(max_length=ID_MAX)


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


class SessionSummaryResponse(BaseModel):
    kind: str  # "ai" for ThinkMate dialogues, "plain" for the worksheet recap
    summary: str
    final_answer: str | None = None


class AnswerRequest(BaseModel):
    answer: str = Field(max_length=LONG_TEXT_MAX)


class AnswerResponse(BaseModel):
    id: str
    final_answer: str


class DialogueTurnRequest(BaseModel):
    session_id: str = Field(max_length=ID_MAX)
    content: str = Field(max_length=LONG_TEXT_MAX)


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


class HintRequest(BaseModel):
    session_id: str = Field(max_length=ID_MAX)


class HintResponse(BaseModel):
    hint: str


class WorksheetResponseRequest(BaseModel):
    session_id: str = Field(max_length=ID_MAX)
    step_key: str = Field(max_length=ID_MAX)
    prompt: str = Field(max_length=SHORT_TEXT_MAX)
    response: str = Field(max_length=LONG_TEXT_MAX)


class WorksheetResponseResponse(BaseModel):
    id: str
    session_id: str
    step_key: str
    response: str

    model_config = ConfigDict(from_attributes=True)


class SessionStateResponse(BaseModel):
    condition: str
    status: str
    final_answer: str | None = None
    turns: list[TurnResponse] = []
    worksheet_responses: list[WorksheetResponseResponse] = []


class FeedbackRequest(BaseModel):
    student_id: str = Field(max_length=ID_MAX)
    rating: int
    comment: str | None = Field(default=None, max_length=SHORT_TEXT_MAX)


class FeedbackResponse(BaseModel):
    id: str
    rating: int
