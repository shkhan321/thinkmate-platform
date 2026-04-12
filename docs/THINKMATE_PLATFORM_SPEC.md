# ThinkMate: Complete Platform Specification

## Master Build Prompt

> **Use this document as a single comprehensive prompt to build the entire ThinkMate platform. Every architectural decision, data model, algorithm, and UI component described here is grounded in the CETL proposal. Sections marked [PRELIMINARY] are functional but will require domain-expert expansion before the pilot launches.**

---

## 1. Project Overview

**ThinkMate** is an AI-powered Socratic tutoring platform that develops critical thinking (CT) skills through constrained, theory-grounded dialogue. It is designed for two pilot courses at UAE University:

- **AERO 590 / MECH 590** — Capstone Engineering Design Project (College of Engineering)
- **PSYC485** — Integrated Capstone (College of Humanities & Social Sciences, Psychology)

### Core Design Principle

ThinkMate **separates pedagogical control from language generation**. A rule-based move selector determines WHAT the tutor should do next. Only after the move is selected does the LLM determine HOW to say it. A safeguard layer then audits the output before delivery. The student never receives a direct answer.

### Three Theoretical Frameworks

Every interaction is grounded in three linked frameworks:

1. **Bloom's Revised Taxonomy** (Anderson & Krathwohl, 2001) — 6 cognitive levels: Remember, Understand, Apply, Analyze, Evaluate, Create
2. **Paul-Elder Critical Thinking Model** (Paul & Elder, 2006) — 6 intellectual standards: Clarity, Accuracy, Depth, Breadth, Logic, Fairness
3. **ICAP Framework** (Chi & Wylie, 2014) — 4 engagement levels: Passive, Active, Constructive, Interactive

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                     │
│  ┌─────────────────────────┐  ┌───────────────────────────┐ │
│  │   Student Dialogue View  │  │  Instructor Dashboard     │ │
│  │   - Chat interface       │  │  - Class analytics        │ │
│  │   - Bloom's level badge  │  │  - Bloom's distribution   │ │
│  │   - Session history      │  │  - Engagement trends      │ │
│  │   - Progress indicator   │  │  - Misconception heatmap  │ │
│  └─────────────────────────┘  └───────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                   WEB APPLICATION LAYER                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  React Frontend (Vite + TypeScript + TailwindCSS)       │ │
│  │  FastAPI Backend (Python 3.11+)                          │ │
│  │  WebSocket for real-time dialogue streaming              │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                     AI CORE MODULES                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │  Student      │ │ Pedagogical  │ │  Socratic Dialogue   │ │
│  │  Modelling    │ │ Strategy     │ │  Engine              │ │
│  │  Agent        │ │ Agent        │ │  (Constrained LLM)   │ │
│  │              │ │              │ │                      │ │
│  │  - Bloom's   │ │ - Move       │ │  - Prompt templates  │ │
│  │    classifier│ │   selector   │ │  - RAG grounding     │ │
│  │  - Paul-Elder│ │ - Decision   │ │  - Answer suppression│ │
│  │    weakness  │ │   matrix     │ │  - Turn generation   │ │
│  │    detector  │ │ - ICAP       │ │                      │ │
│  │              │ │   classifier │ │                      │ │
│  └──────┬───────┘ └──────┬───────┘ └──────────┬───────────┘ │
│         │                │                     │             │
│  ┌──────┴────────────────┴─────────────────────┴───────────┐ │
│  │              SAFEGUARD LAYER                             │ │
│  │  - Answer leakage detector                               │ │
│  │  - Factual accuracy check (RAG validation)               │ │
│  │  - Premature closure detector                            │ │
│  │  - Fallback template trigger                             │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                      DATA LAYER                              │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐ │
│  │  PostgreSQL     │ │  Vector Store  │ │  Dialogue Log    │ │
│  │  - Users        │ │  (ChromaDB)    │ │  Storage         │ │
│  │  - Sessions     │ │  - Course docs │ │  - Per-turn logs │ │
│  │  - Assessments  │ │  - Rubrics     │ │  - Move tags     │ │
│  │  - Analytics    │ │  - Misconceptions│ │  - ICAP states  │ │
│  └────────────────┘ └────────────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + TypeScript + Vite + TailwindCSS | Modern, fast, type-safe |
| UI Components | shadcn/ui | Accessible, customisable |
| State Management | Zustand | Lightweight, minimal boilerplate |
| Backend | FastAPI (Python 3.11+) | Async, fast, auto-docs |
| Database | PostgreSQL 15+ | Relational, robust, JSONB for logs |
| Vector Store | ChromaDB (self-hosted) | RAG, open-source, no vendor lock |
| LLM Provider | OpenAI GPT-4o (primary) | Best reasoning quality |
| LLM Fallback | Llama 3.1 70B via Ollama | Cost control, offline capability |
| Real-time | WebSocket (FastAPI) | Streaming dialogue responses |
| Authentication | JWT + OAuth2 (UAEU SSO) | Institutional integration |
| Deployment | Docker + Docker Compose | Reproducible, portable |
| Hosting | UAEU-hosted server or AWS/Azure | Data sovereignty compliance |

---

## 4. Data Models

### 4.1 Database Schema (PostgreSQL)

```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'instructor', 'admin')),
    student_id VARCHAR(50),                    -- UAEU student ID
    college VARCHAR(100),
    department VARCHAR(100),
    course_id UUID REFERENCES courses(id),
    experimental_group VARCHAR(5),             -- 'A' or 'B' for crossover design
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Courses
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL,                 -- 'AERO590', 'PSYC485'
    name VARCHAR(255) NOT NULL,
    college VARCHAR(100) NOT NULL,
    instructor_id UUID REFERENCES users(id),
    semester VARCHAR(20) NOT NULL,             -- 'Fall2026'
    discipline_module VARCHAR(50) NOT NULL,    -- 'engineering', 'psychology'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dialogue Sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    course_id UUID REFERENCES courses(id) NOT NULL,
    task_id UUID REFERENCES tasks(id),
    condition VARCHAR(20) NOT NULL CHECK (condition IN ('thinkmate', 'guided_worksheet')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    total_turns INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    final_blooms_level VARCHAR(20),
    final_icap_level VARCHAR(20),
    usability_score DECIMAL(4,2),             -- SUS score post-session
    is_complete BOOLEAN DEFAULT false
);

-- Individual Dialogue Turns
CREATE TABLE turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) NOT NULL,
    turn_number INTEGER NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('student', 'tutor', 'system')),
    content TEXT NOT NULL,
    
    -- Pedagogical metadata (logged every turn)
    intended_move VARCHAR(30),                -- clarification, evidence_probe, assumption_probe,
                                               -- counterview_challenge, synthesis_prompt, reflection_cue
    targeted_paul_elder VARCHAR(20),          -- clarity, accuracy, depth, breadth, logic, fairness
    detected_blooms_level VARCHAR(20),        -- remember, understand, apply, analyze, evaluate, create
    detected_paul_elder_weakness VARCHAR(20), -- which standard the student was weak on
    icap_classification VARCHAR(20),          -- passive, active, constructive, interactive
    
    -- Safeguard flags
    answer_leakage_flagged BOOLEAN DEFAULT false,
    safeguard_override_used BOOLEAN DEFAULT false,
    factual_accuracy_score DECIMAL(3,2),      -- 0.0 to 1.0
    
    -- Metadata
    response_time_ms INTEGER,                 -- student response latency
    token_count INTEGER,
    model_used VARCHAR(50),                   -- 'gpt-4o', 'llama-3.1-70b'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pilot Tasks (for crossover design)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) NOT NULL,
    task_number INTEGER NOT NULL CHECK (task_number IN (1, 2)),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    rubric JSONB NOT NULL,                    -- Paul-Elder-aligned scoring rubric
    expected_blooms_range VARCHAR(50),        -- e.g., 'analyze-evaluate'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Assessment Scores (blinded rubric scoring)
CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) NOT NULL,
    task_id UUID REFERENCES tasks(id) NOT NULL,
    rater_id VARCHAR(50) NOT NULL,            -- anonymised rater identifier
    rater_number INTEGER NOT NULL CHECK (rater_number IN (1, 2, 3)),
    
    -- Paul-Elder standard scores (each 1-5)
    clarity_score INTEGER CHECK (clarity_score BETWEEN 1 AND 5),
    accuracy_score INTEGER CHECK (accuracy_score BETWEEN 1 AND 5),
    depth_score INTEGER CHECK (depth_score BETWEEN 1 AND 5),
    breadth_score INTEGER CHECK (breadth_score BETWEEN 1 AND 5),
    logic_score INTEGER CHECK (logic_score BETWEEN 1 AND 5),
    fairness_score INTEGER CHECK (fairness_score BETWEEN 1 AND 5),
    overall_reasoning_score DECIMAL(3,2),     -- composite
    
    comments TEXT,
    scored_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prompt Libraries [PRELIMINARY — content to be authored by Humanities team]
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discipline VARCHAR(50) NOT NULL,          -- 'engineering', 'psychology'
    move_type VARCHAR(30) NOT NULL,           -- matches intended_move values
    blooms_level VARCHAR(20) NOT NULL,
    paul_elder_target VARCHAR(20) NOT NULL,
    template_text TEXT NOT NULL,              -- with {placeholders}
    example_realisation TEXT,
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Misconception Maps [PRELIMINARY — to be populated during co-design phase]
CREATE TABLE misconceptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discipline VARCHAR(50) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    misconception TEXT NOT NULL,
    correct_understanding TEXT NOT NULL,
    common_triggers TEXT[],                   -- student phrases that indicate this misconception
    suggested_move VARCHAR(30),               -- recommended Socratic move to address it
    blooms_level VARCHAR(20),
    source VARCHAR(255),                      -- literature or instructor source
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector Store Documents (metadata tracked in PG, embeddings in ChromaDB)
CREATE TABLE rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id),
    discipline VARCHAR(50) NOT NULL,
    document_type VARCHAR(50) NOT NULL,       -- 'lecture_notes', 'rubric', 'textbook_excerpt', 'misconception_map'
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    chromadb_collection VARCHAR(100) NOT NULL,
    chunk_count INTEGER,
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- SUS Survey Responses
CREATE TABLE sus_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    session_id UUID REFERENCES sessions(id),
    q1 INTEGER CHECK (q1 BETWEEN 1 AND 5),   -- I think I would like to use this system frequently
    q2 INTEGER CHECK (q2 BETWEEN 1 AND 5),   -- I found the system unnecessarily complex
    q3 INTEGER CHECK (q3 BETWEEN 1 AND 5),   -- I thought the system was easy to use
    q4 INTEGER CHECK (q4 BETWEEN 1 AND 5),   -- I think I would need technical support
    q5 INTEGER CHECK (q5 BETWEEN 1 AND 5),   -- I found the functions well integrated
    q6 INTEGER CHECK (q6 BETWEEN 1 AND 5),   -- I thought there was too much inconsistency
    q7 INTEGER CHECK (q7 BETWEEN 1 AND 5),   -- I imagine most people would learn quickly
    q8 INTEGER CHECK (q8 BETWEEN 1 AND 5),   -- I found the system very cumbersome
    q9 INTEGER CHECK (q9 BETWEEN 1 AND 5),   -- I felt very confident using the system
    q10 INTEGER CHECK (q10 BETWEEN 1 AND 5), -- I needed to learn a lot before I could get going
    sus_total DECIMAL(5,2),                   -- calculated: ((sum of odd-1) + (5-sum of even)) * 2.5
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 Vector Store Schema (ChromaDB)

```python
# Collections:
# - engineering_course_materials
# - psychology_course_materials  
# - misconception_maps
# - rubric_definitions

# Each document chunk stored with metadata:
{
    "id": "doc_chunk_uuid",
    "document": "chunk text content",
    "metadata": {
        "source_doc_id": "uuid",
        "discipline": "engineering",
        "document_type": "lecture_notes",
        "topic": "fatigue analysis",
        "chunk_index": 3,
        "blooms_relevance": ["analyze", "evaluate"]
    }
}
```

---

## 5. AI Core — The Heart of ThinkMate

### 5.1 Student Modelling Agent

This agent classifies each student response along two dimensions:

#### Bloom's Level Classifier

```python
BLOOMS_LEVELS = {
    "remember": {
        "description": "Recalls facts, terms, or definitions without elaboration",
        "indicators": ["states facts", "lists items", "defines terms", "repeats content"],
        "numeric_level": 1
    },
    "understand": {
        "description": "Explains concepts in own words, paraphrases, summarises",
        "indicators": ["explains", "paraphrases", "summarises", "gives examples"],
        "numeric_level": 2
    },
    "apply": {
        "description": "Uses knowledge in a new situation without being told how",
        "indicators": ["applies to new context", "uses procedure", "solves similar problem"],
        "numeric_level": 3
    },
    "analyze": {
        "description": "Breaks information into parts, identifies relationships, distinguishes",
        "indicators": ["compares", "contrasts", "identifies assumptions", "examines evidence",
                       "distinguishes cause from correlation"],
        "numeric_level": 4
    },
    "evaluate": {
        "description": "Makes judgements based on criteria, justifies positions",
        "indicators": ["judges", "critiques", "weighs evidence", "justifies decision",
                       "assesses strength of argument"],
        "numeric_level": 5
    },
    "create": {
        "description": "Generates new ideas, designs, synthesises from multiple sources",
        "indicators": ["proposes new solution", "synthesises", "designs", "hypothesises"],
        "numeric_level": 6
    }
}
```

**Classification method:** LLM-based classifier with structured output. The classifier receives the student's response plus the conversation history and returns:

```python
class StudentModelOutput(BaseModel):
    blooms_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    blooms_confidence: float  # 0.0 to 1.0
    paul_elder_weaknesses: list[Literal["clarity", "accuracy", "depth", "breadth", "logic", "fairness"]]
    primary_weakness: Literal["clarity", "accuracy", "depth", "breadth", "logic", "fairness"]
    weakness_evidence: str  # specific quote or pattern from student response
    response_type: Literal["claim", "evidence", "reasoning", "question", "acknowledgement", "deflection"]
```

**Classification prompt template:**

```
You are a cognitive assessment specialist. Analyse the student's most recent 
response in the context of the ongoing Socratic dialogue.

CONVERSATION HISTORY:
{conversation_history}

STUDENT'S LATEST RESPONSE:
{student_response}

TASK CONTEXT:
{task_description}

Classify the response on TWO dimensions:

1. BLOOM'S COGNITIVE LEVEL: Which level best describes the thinking demonstrated?
   - Remember: Merely recalls or restates facts
   - Understand: Explains in own words but does not go further
   - Apply: Uses concept in a new context
   - Analyze: Breaks apart, identifies assumptions, examines relationships
   - Evaluate: Makes evidence-based judgements, weighs alternatives
   - Create: Synthesises or proposes original solutions

2. PAUL-ELDER WEAKNESS: Which intellectual standard is most deficient?
   - Clarity: Response is vague, ambiguous, or imprecise
   - Accuracy: Claims are unsupported or potentially incorrect
   - Depth: Response is superficial, does not address complexity
   - Breadth: Only one perspective considered, alternatives ignored
   - Logic: Reasoning contains contradictions or non sequiturs
   - Fairness: Exhibits bias or fails to consider opposing viewpoints

Return ONLY valid JSON matching the required schema.
```

#### Paul-Elder Weakness Detector

Each Paul-Elder standard has detection heuristics:

| Standard | Detection Signals |
|----------|------------------|
| **Clarity** | Vague language, undefined terms, ambiguous pronouns, "it depends" without specification |
| **Accuracy** | Unsupported claims, factual errors (checked against RAG), overgeneralisations |
| **Depth** | Surface-level responses, missing causal mechanisms, no engagement with complexity |
| **Breadth** | Single perspective, no counterarguments, missing stakeholder views |
| **Logic** | Non sequiturs, circular reasoning, contradictions with prior statements |
| **Fairness** | Straw-man framing, dismissal of opposing evidence, motivated reasoning |

### 5.2 Constrained Move Selector (Rule-Based)

The move selector is the **core novelty** of ThinkMate. It operates as a deterministic decision matrix that maps the student model output to one of six Socratic moves.

#### Six Socratic Moves

```python
SOCRATIC_MOVES = {
    "clarification_request": {
        "description": "Ask the student to be more precise or define key terms",
        "triggers_on_weakness": "clarity",
        "paul_elder_target": "clarity",
        "example": "What exactly do you mean by 'the material failed'? Can you be more specific about the failure mechanism?"
    },
    "evidence_probe": {
        "description": "Ask what evidence supports the student's claim",
        "triggers_on_weakness": "accuracy",
        "paul_elder_target": "accuracy",
        "example": "What evidence allows you to conclude that fatigue was the primary cause rather than static overload?"
    },
    "assumption_probe": {
        "description": "Surface a hidden assumption in the student's reasoning",
        "triggers_on_weakness": "depth",
        "paul_elder_target": "depth",
        "example": "You seem to be assuming the load was constant. What if the loading history was cyclic — how would that change your analysis?"
    },
    "counterview_challenge": {
        "description": "Present an alternative perspective or counterargument",
        "triggers_on_weakness": "breadth",
        "paul_elder_target": "breadth",
        "example": "A structural engineer might disagree with that conclusion. What would someone focused on environmental factors argue instead?"
    },
    "synthesis_prompt": {
        "description": "Ask the student to integrate multiple pieces of reasoning",
        "triggers_on_weakness": "logic",
        "paul_elder_target": "logic",
        "example": "You've identified three contributing factors. How do they relate to each other, and which one carries the most explanatory weight?"
    },
    "reflection_cue": {
        "description": "Ask the student to evaluate their own reasoning process",
        "triggers_on_weakness": "fairness",
        "paul_elder_target": "fairness",
        "example": "Looking back at your reasoning, are there any perspectives you might have underweighted or dismissed too quickly?"
    }
}
```

#### Decision Matrix

```python
def select_move(student_model: StudentModelOutput, session_history: list[Turn]) -> str:
    """
    Rule-based move selection. Returns one of the six Socratic moves.
    
    RULES (applied in priority order):
    
    1. ESCALATION RULE: If the student has been at the same Bloom's level
       for 3+ consecutive turns, escalate to a move that targets the next 
       higher level.
    
    2. PRIMARY WEAKNESS RULE: Map the detected Paul-Elder weakness directly
       to its corresponding Socratic move.
    
    3. VARIETY RULE: If the same move has been used in the last 2 turns,
       select the next-best move based on secondary weaknesses.
    
    4. BLOOM'S PROGRESSION RULE: If the student is at remember/understand,
       prefer clarification_request or evidence_probe. If at analyze/evaluate,
       prefer counterview_challenge or synthesis_prompt. If at create,
       prefer reflection_cue.
    
    5. DEFLECTION RULE: If the student's response is classified as 
       'deflection' or 'acknowledgement' (passive engagement), use
       assumption_probe to re-engage with a concrete challenge.
    
    6. COMPLETION CHECK: If the student has demonstrated evaluate or create
       level with no remaining weaknesses across 2+ consecutive turns,
       issue a reflection_cue to close the dialogue constructively.
    """
    
    # Priority 1: Deflection handling
    if student_model.response_type in ("deflection", "acknowledgement"):
        return "assumption_probe"
    
    # Priority 2: Escalation after stagnation
    recent_levels = [t.detected_blooms_level for t in session_history[-3:]]
    if len(set(recent_levels)) == 1 and len(recent_levels) >= 3:
        return _escalation_move(student_model.blooms_level)
    
    # Priority 3: Primary weakness mapping
    primary_move = WEAKNESS_TO_MOVE[student_model.primary_weakness]
    
    # Priority 4: Variety check
    recent_moves = [t.intended_move for t in session_history[-2:]]
    if primary_move in recent_moves:
        # Use secondary weakness
        for weakness in student_model.paul_elder_weaknesses:
            alt_move = WEAKNESS_TO_MOVE[weakness]
            if alt_move not in recent_moves:
                return alt_move
    
    # Priority 5: Bloom's alignment
    if student_model.blooms_level in ("remember", "understand"):
        if primary_move in ("synthesis_prompt", "reflection_cue"):
            return "evidence_probe"  # don't ask for synthesis at low levels
    
    return primary_move


WEAKNESS_TO_MOVE = {
    "clarity":   "clarification_request",
    "accuracy":  "evidence_probe",
    "depth":     "assumption_probe",
    "breadth":   "counterview_challenge",
    "logic":     "synthesis_prompt",
    "fairness":  "reflection_cue",
}
```

### 5.3 ICAP Engagement Classifier

Classifies each student turn into an ICAP engagement level:

```python
class ICAPClassifier:
    """
    Classification method: keyword density + response length + LLM semantic check.
    Validated against human-coded samples; target agreement >= 80%.
    """
    
    CLASSIFICATION_RULES = {
        "passive": {
            "description": "Minimal engagement — short acknowledgements, single-word answers",
            "signals": [
                "response length < 15 words",
                "contains only 'yes', 'no', 'okay', 'I agree', 'I see'",
                "restates tutor's question without adding content",
                "no new information introduced"
            ]
        },
        "active": {
            "description": "Engages with material but does not generate new reasoning",
            "signals": [
                "restates or paraphrases existing content",
                "selects from given options without justification",
                "copies/references source material without elaboration",
                "response length 15-50 words with no novel claims"
            ]
        },
        "constructive": {
            "description": "Generates new reasoning, explanations, or connections",
            "signals": [
                "introduces explanation not present in prior turns",
                "makes connections between concepts",
                "generates own examples or analogies",
                "provides justification for a claim",
                "response length > 50 words with novel content"
            ]
        },
        "interactive": {
            "description": "Revises position after challenge, integrates feedback",
            "signals": [
                "explicitly changes or refines prior claim",
                "acknowledges a flaw in previous reasoning",
                "integrates tutor's challenge into revised position",
                "synthesises own view with alternative perspective",
                "builds on a counterview to produce stronger argument"
            ]
        }
    }
```

### 5.4 Dialogue Engine (Constrained LLM Generation)

The dialogue engine generates the natural-language realisation of the selected move.

```python
DIALOGUE_GENERATION_SYSTEM_PROMPT = """
You are a Socratic tutor named ThinkMate. Your ONLY role is to help students 
develop stronger reasoning through questioning. You operate under strict rules:

ABSOLUTE RULES (never violate):
1. NEVER give the student a direct answer, solution, or conclusion.
2. NEVER confirm whether the student's answer is correct or incorrect.
3. NEVER introduce new factual content that the student has not raised.
4. NEVER use more than 3 sentences per turn.
5. NEVER use leading questions that telegraph the expected answer.
6. ALWAYS ask exactly ONE question per turn.
7. ALWAYS ground your question in what the student just said.

YOUR TASK THIS TURN:
- Execute the Socratic move: {selected_move}
- Target the Paul-Elder standard: {targeted_standard}
- The student is currently at Bloom's level: {current_blooms}
- Detected weakness: {weakness_description}

RELEVANT COURSE CONTEXT (from verified materials):
{rag_context}

CONVERSATION SO FAR:
{conversation_history}

STUDENT'S LATEST RESPONSE:
{student_response}

Generate a single Socratic question that executes the specified move.
Do NOT explain why you are asking the question.
Do NOT add encouragement or praise.
Keep the tone neutral, direct, and intellectually challenging.
"""
```

#### RAG Integration

Every generated question is grounded in instructor-vetted course materials:

```python
async def get_rag_context(student_response: str, discipline: str, topic: str) -> str:
    """
    Retrieve relevant course material chunks from ChromaDB.
    This ensures Socratic questions reference verified disciplinary content
    rather than unconstrained LLM knowledge, mitigating hallucination risk.
    """
    collection = chroma_client.get_collection(f"{discipline}_course_materials")
    results = collection.query(
        query_texts=[student_response],
        n_results=3,
        where={"discipline": discipline}
    )
    return "\n---\n".join(results["documents"][0])
```

### 5.5 Safeguard Layer

Every tutor response passes through three safeguard checks before delivery:

```python
class SafeguardLayer:
    """
    Three-stage audit pipeline. If ANY check fails, the response is 
    replaced with a fallback template prompt.
    """
    
    async def audit(self, tutor_response: str, context: DialogueContext) -> SafeguardResult:
        # Check 1: Answer Leakage Detection
        leakage = await self.check_answer_leakage(tutor_response, context)
        
        # Check 2: Factual Accuracy (RAG validation)
        accuracy = await self.check_factual_accuracy(tutor_response, context)
        
        # Check 3: Premature Closure Detection
        closure = await self.check_premature_closure(tutor_response, context)
        
        if not all([leakage.passed, accuracy.passed, closure.passed]):
            return SafeguardResult(
                passed=False,
                replacement=self.get_fallback_template(context.selected_move),
                flags={"leakage": not leakage.passed, 
                       "accuracy": not accuracy.passed,
                       "closure": not closure.passed}
            )
        return SafeguardResult(passed=True)
    
    async def check_answer_leakage(self, response: str, ctx: DialogueContext) -> CheckResult:
        """
        Uses an LLM judge to determine if the tutor's response reveals,
        implies, or strongly hints at the answer. 
        
        Prompt to the judge:
        'Does this tutor response give away the answer, confirm/deny the 
        student's position, or make it obvious what the correct answer is? 
        Respond YES or NO with a brief explanation.'
        """
        ...
    
    async def check_factual_accuracy(self, response: str, ctx: DialogueContext) -> CheckResult:
        """
        Verifies that any factual claims in the question are consistent
        with RAG-retrieved course materials. Flags responses that introduce
        content not found in the vetted material.
        """
        ...
    
    async def check_premature_closure(self, response: str, ctx: DialogueContext) -> CheckResult:
        """
        Detects if the tutor is wrapping up too early (e.g., 'Great job!',
        'That's correct!', 'You've got it!'). Dialogue should only end
        via explicit session completion, not tutor praise.
        """
        CLOSURE_PATTERNS = [
            r"great job", r"well done", r"exactly right", r"perfect",
            r"that's correct", r"you've got it", r"excellent answer"
        ]
        ...

    def get_fallback_template(self, move_type: str) -> str:
        """Returns a safe, pre-written fallback question for the given move type."""
        FALLBACKS = {
            "clarification_request": "Can you restate that more precisely — what specifically are you referring to?",
            "evidence_probe": "What evidence from the course material supports that claim?",
            "assumption_probe": "What assumption is your reasoning relying on, and what if that assumption were wrong?",
            "counterview_challenge": "What would someone who disagrees with you argue, and how would you respond?",
            "synthesis_prompt": "How do the different factors you've mentioned connect to each other?",
            "reflection_cue": "Looking back at this conversation, what has changed in your thinking and why?"
        }
        return FALLBACKS.get(move_type, FALLBACKS["reflection_cue"])
```

---

## 6. Bloom's Taxonomy Prompt Strategy Mapping

[PRELIMINARY — The prompt templates below are starting points. The Humanities team (Laiya and Salma) will author discipline-specific expansions during Phase 2.]

| Bloom's Level | Example Socratic Prompt | Paul-Elder Standard Targeted |
|--------------|------------------------|------------------------------|
| Remember | What do you recall about X? | Clarity |
| Understand | Can you explain this concept in your own words? | Accuracy |
| Apply | How would you use this principle in a different context? | Relevance / Accuracy |
| Analyze | What evidence supports your claim? What assumptions are you making? | Depth |
| Evaluate | Which explanation is better supported and why? | Logic |
| Create | Propose an alternative solution and justify it. | Breadth |

---

## 7. Frontend Specification

### 7.1 Student Dialogue View

```
┌─────────────────────────────────────────────────────┐
│  ThinkMate              AERO 590 | Task 1     [End] │
├──────┬──────────────────────────────────────────────┤
│      │                                              │
│  B   │  ┌──────────────────────────────────────┐   │
│  L   │  │ ThinkMate                             │   │
│  O   │  │ What evidence allows you to separate  │   │
│  O   │  │ material weakness from loading or     │   │
│  M   │  │ design assumptions?                   │   │
│  '   │  │ [Analyze · Accuracy]                  │   │
│  S   │  └──────────────────────────────────────┘   │
│      │                                              │
│  L   │  ┌──────────────────────────────────────┐   │
│  E   │  │                        Student        │   │
│  V   │  │ I assumed the load was constant, so   │   │
│  E   │  │ I focused on the steel grade itself.  │   │
│  L   │  └──────────────────────────────────────┘   │
│      │                                              │
│ ┌──┐ │  ┌──────────────────────────────────────┐   │
│ │An│ │  │ ThinkMate                             │   │
│ │al│ │  │ What assumption are you making about  │   │
│ │yz│ │  │ the loading history, and how might    │   │
│ │e │ │  │ cyclic loading change your            │   │
│ │  │ │  │ explanation?                          │   │
│ │▲ │ │  │ [Analyze · Depth]                     │   │
│ └──┘ │  └──────────────────────────────────────┘   │
│      │                                              │
│      │  ┌──────────────────────────────────┐       │
│      │  │ Type your response...        [→] │       │
│      │  └──────────────────────────────────┘       │
├──────┴──────────────────────────────────────────────┤
│  Turn 4/20  |  Session: 12 min  |  Progress: ████░ │
└─────────────────────────────────────────────────────┘
```

**Key UI Components:**
- Left sidebar: Bloom's Level Indicator (vertical colour bar showing current level)
- Chat area: Alternating tutor/student messages
- Each tutor message shows small tags: `[Bloom's Level · Paul-Elder Standard]`
- Input area with send button
- Bottom status bar: turn count, session duration, progress indicator
- Session ends after 20 turns or when student clicks End
- Students do NOT see ICAP classification (that is logged silently)

### 7.2 Instructor Analytics Dashboard

```
┌──────────────────────────────────────────────────────────┐
│  ThinkMate Dashboard         AERO 590 | Fall 2026        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────┐  ┌────────────────────────────┐ │
│  │ Bloom's Distribution│  │ Engagement Trends (ICAP)   │ │
│  │                     │  │                            │ │
│  │  [Stacked bar chart │  │  [Line chart showing       │ │
│  │   showing class-wide│  │   P/A/C/I proportions      │ │
│  │   Bloom's levels    │  │   over sessions]           │ │
│  │   per session]      │  │                            │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────┐  ┌────────────────────────────┐ │
│  │ Common Misconceptions│  │ Quick Stats               │ │
│  │                     │  │                            │ │
│  │  [Horizontal bar    │  │  Total Sessions: 142       │ │
│  │   chart of top 5    │  │  Avg Turns: 15.4           │ │
│  │   misconceptions]   │  │  Completion Rate: 88%      │ │
│  │                     │  │  Safeguard Fidelity: 92%   │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Paul-Elder Weakness Heatmap                          │ │
│  │                                                      │ │
│  │  [Heatmap: students (rows) x standards (columns)     │ │
│  │   showing which standards each student struggles with]│ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Session Dialogue Viewer (click any session to review)│ │
│  │  [Filterable table of all sessions with Bloom's,     │ │
│  │   ICAP, turns, duration, safeguard flags]            │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Dashboard Charts (use Recharts or Chart.js):**
1. Bloom's Level Distribution — stacked bar per session/week
2. ICAP Engagement Trends — line chart over time
3. Common Misconceptions — horizontal bar chart (top 5 per topic)
4. Paul-Elder Weakness Heatmap — student x standard matrix
5. Quick Stats — cards with key metrics
6. Session Dialogue Viewer — clickable table to review individual dialogues
7. Safeguard Fidelity Report — % of turns that passed all 3 safeguard checks

---

## 8. API Endpoints

### 8.1 Authentication
```
POST   /api/auth/login           — JWT login
POST   /api/auth/refresh         — Refresh token
GET    /api/auth/me              — Current user profile
```

### 8.2 Dialogue
```
POST   /api/dialogue/start       — Start new session (returns session_id)
POST   /api/dialogue/turn        — Submit student response, get tutor response
GET    /api/dialogue/session/{id} — Get full session history
POST   /api/dialogue/end         — End session, trigger SUS survey
WS     /api/dialogue/stream/{session_id} — WebSocket for streaming responses
```

### 8.3 Tasks & Courses
```
GET    /api/courses              — List user's courses
GET    /api/courses/{id}/tasks   — Get tasks for a course
GET    /api/tasks/{id}           — Get task details + rubric
```

### 8.4 Dashboard (Instructor-only)
```
GET    /api/dashboard/overview/{course_id}     — Quick stats
GET    /api/dashboard/blooms/{course_id}       — Bloom's distribution data
GET    /api/dashboard/icap/{course_id}         — ICAP engagement trends
GET    /api/dashboard/misconceptions/{course_id} — Misconception frequency
GET    /api/dashboard/heatmap/{course_id}      — Paul-Elder weakness heatmap
GET    /api/dashboard/sessions/{course_id}     — All sessions with filters
GET    /api/dashboard/session/{session_id}     — Individual session detail
GET    /api/dashboard/safeguard/{course_id}    — Safeguard fidelity report
GET    /api/dashboard/export/{course_id}       — CSV export for analysis
```

### 8.5 Assessment (Rater interface)
```
GET    /api/assessments/pending                — Get unscored artifacts
POST   /api/assessments/score                  — Submit rubric scores
GET    /api/assessments/icc/{task_id}          — Inter-rater reliability
```

### 8.6 Admin
```
POST   /api/admin/upload-materials             — Upload course materials to RAG
POST   /api/admin/prompt-templates             — CRUD prompt templates
GET    /api/admin/token-usage                  — API cost monitoring
POST   /api/admin/randomise/{course_id}        — Generate crossover randomisation
```

---

## 9. Crossover Experimental Design Integration

The platform natively supports the counterbalanced crossover pilot design:

```python
class CrossoverManager:
    """
    Students randomised to Sequence A or B.
    
    Sequence A: Task 1 = ThinkMate,          Task 2 = Guided Worksheet
    Sequence B: Task 1 = Guided Worksheet,   Task 2 = ThinkMate
    
    The platform automatically routes students to the correct condition
    based on their assigned sequence and the current active task.
    """
    
    def get_condition(self, user: User, task: Task) -> str:
        if user.experimental_group == "A":
            return "thinkmate" if task.task_number == 1 else "guided_worksheet"
        else:
            return "guided_worksheet" if task.task_number == 1 else "thinkmate"
    
    def randomise_course(self, course_id: UUID) -> dict:
        """
        Stratified randomisation by college (to ensure balance).
        Returns assignment mapping.
        """
        students = get_students_by_course(course_id)
        # Stratify by college, then randomise within strata
        ...
```

**Guided Worksheet Condition:** When a student is in the guided_worksheet condition, the platform serves a structured reasoning worksheet through the same interface (not ThinkMate). The worksheet mirrors the same reasoning sequence (claim → evidence → assumption → counterargument → revision → reflection) but without individualised Socratic probing. This is delivered as a sequential form, not an AI dialogue.

---

## 10. Logging & Analytics Pipeline

Every dialogue turn generates a structured log entry:

```python
class TurnLog(BaseModel):
    """Logged to PostgreSQL turns table on every single turn."""
    session_id: UUID
    turn_number: int
    role: Literal["student", "tutor"]
    content: str
    
    # Pedagogical metadata
    intended_move: str | None           # null for student turns
    targeted_paul_elder: str | None
    detected_blooms_level: str
    detected_paul_elder_weakness: str
    icap_classification: str
    
    # Safeguard flags
    answer_leakage_flagged: bool
    safeguard_override_used: bool
    factual_accuracy_score: float
    
    # Performance
    response_time_ms: int
    token_count: int
    model_used: str
    timestamp: datetime
```

**Analytics queries (pre-built for the dashboard):**
- Mean dialogue depth per student, per course, per condition
- Bloom's level progression curves (first turn → last turn per session)
- ICAP distribution shifts pre/post across conditions
- Safeguard fidelity rate (% turns passing all 3 checks)
- Misconception frequency ranking
- Token usage and cost tracking (daily, weekly, cumulative)
- Time-on-task per condition (for controlling engagement duration)

---

## 11. Deployment & Infrastructure

### Docker Compose Stack

```yaml
# docker-compose.yml
version: "3.9"
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://thinkmate:${DB_PASSWORD}@db:5432/thinkmate
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8001
      - JWT_SECRET=${JWT_SECRET}
      - ENVIRONMENT=production
      - TOKEN_BUDGET_DAILY=50000    # daily token cap for cost control
      - TOKEN_BUDGET_WEEKLY=300000
    depends_on:
      - db
      - chromadb

  db:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/db/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      - POSTGRES_DB=thinkmate
      - POSTGRES_USER=thinkmate
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    ports:
      - "5432:5432"

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chromadata:/chroma/chroma
    ports:
      - "8001:8000"

volumes:
  pgdata:
  chromadata:
```

### Environment Variables (.env — NEVER commit)
```
DB_PASSWORD=<strong-random-password>
OPENAI_API_KEY=sk-...
JWT_SECRET=<strong-random-secret>
OPENAI_MODEL=gpt-4o
FALLBACK_MODEL=llama-3.1-70b
TOKEN_BUDGET_DAILY=50000
TOKEN_BUDGET_WEEKLY=300000
```

---

## 12. Directory Structure

```
thinkmate-platform/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── dialogue/
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   ├── BloomsIndicator.tsx
│   │   │   │   ├── InputArea.tsx
│   │   │   │   └── SessionStatus.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── DashboardLayout.tsx
│   │   │   │   ├── BloomsDistributionChart.tsx
│   │   │   │   ├── ICAPTrendsChart.tsx
│   │   │   │   ├── MisconceptionChart.tsx
│   │   │   │   ├── PaulElderHeatmap.tsx
│   │   │   │   ├── QuickStats.tsx
│   │   │   │   ├── SafeguardReport.tsx
│   │   │   │   └── SessionViewer.tsx
│   │   │   ├── worksheet/
│   │   │   │   └── GuidedWorksheet.tsx      -- non-AI comparison condition
│   │   │   ├── assessment/
│   │   │   │   └── RubricScorer.tsx          -- blinded rater interface
│   │   │   ├── auth/
│   │   │   │   ├── LoginPage.tsx
│   │   │   │   └── ProtectedRoute.tsx
│   │   │   └── ui/                           -- shadcn/ui components
│   │   ├── stores/
│   │   │   ├── authStore.ts
│   │   │   ├── dialogueStore.ts
│   │   │   └── dashboardStore.ts
│   │   ├── api/
│   │   │   └── client.ts                     -- Axios/fetch wrapper
│   │   ├── types/
│   │   │   └── index.ts                      -- TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── backend/
│   ├── app/
│   │   ├── main.py                           -- FastAPI app entry
│   │   ├── config.py                         -- Settings, env vars
│   │   ├── models/
│   │   │   ├── database.py                   -- SQLAlchemy models
│   │   │   └── schemas.py                    -- Pydantic schemas
│   │   ├── api/
│   │   │   ├── auth.py                       -- Authentication routes
│   │   │   ├── dialogue.py                   -- Dialogue routes + WebSocket
│   │   │   ├── dashboard.py                  -- Dashboard analytics routes
│   │   │   ├── assessment.py                 -- Rubric scoring routes
│   │   │   ├── admin.py                      -- Admin routes
│   │   │   └── tasks.py                      -- Course/task routes
│   │   ├── core/
│   │   │   ├── student_model.py              -- Bloom's + Paul-Elder classifier
│   │   │   ├── move_selector.py              -- Rule-based move selection
│   │   │   ├── dialogue_engine.py            -- Constrained LLM generation
│   │   │   ├── icap_classifier.py            -- ICAP engagement classification
│   │   │   ├── safeguard_layer.py            -- 3-stage audit pipeline
│   │   │   ├── rag_manager.py                -- ChromaDB retrieval
│   │   │   └── crossover_manager.py          -- Experimental design logic
│   │   ├── services/
│   │   │   ├── llm_service.py                -- OpenAI / fallback model client
│   │   │   ├── token_tracker.py              -- Cost monitoring + caps
│   │   │   └── analytics_service.py          -- Dashboard query builders
│   │   └── db/
│   │       ├── init.sql                      -- Full schema
│   │       └── seed_data.py                  -- Seed prompt templates, demo data
│   ├── tests/
│   │   ├── test_move_selector.py
│   │   ├── test_safeguard_layer.py
│   │   ├── test_student_model.py
│   │   ├── test_icap_classifier.py
│   │   └── test_dialogue_integration.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic/                              -- DB migrations
│       └── ...
│
├── prompt_libraries/                         [PRELIMINARY]
│   ├── engineering/
│   │   ├── clarification_templates.json
│   │   ├── evidence_probe_templates.json
│   │   ├── assumption_probe_templates.json
│   │   ├── counterview_templates.json
│   │   ├── synthesis_templates.json
│   │   ├── reflection_templates.json
│   │   └── misconception_map.json
│   └── psychology/
│       ├── clarification_templates.json
│       ├── evidence_probe_templates.json
│       ├── assumption_probe_templates.json
│       ├── counterview_templates.json
│       ├── synthesis_templates.json
│       ├── reflection_templates.json
│       └── misconception_map.json
│
├── course_materials/                         [PRELIMINARY — to be populated]
│   ├── engineering/
│   │   └── README.md                         -- Upload lecture notes, rubrics here
│   └── psychology/
│       └── README.md                         -- Upload lecture notes, rubrics here
│
├── docs/
│   ├── THINKMATE_PLATFORM_SPEC.md            -- This file
│   ├── API_REFERENCE.md                      -- Auto-generated from FastAPI
│   ├── DEPLOYMENT_GUIDE.md
│   └── RED_TEAM_TESTING_PROTOCOL.md          [PRELIMINARY]
│
├── site/                                     -- GitHub Pages landing page
│   └── index.html
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 13. Items Marked [PRELIMINARY] — Requiring Expansion

These components are structurally complete but require domain-expert content before the pilot:

| Component | What Exists Now | What Needs Expansion | Who |
|-----------|----------------|---------------------|-----|
| **Prompt Libraries** | 6 template files per discipline with structure and 2-3 examples each | 15-20 templates per move type per discipline, covering common topics | Laiya (Psychology), Co-PI review |
| **Misconception Maps** | Schema and example entries | Full maps for each pilot course topic (5-10 misconceptions per topic) | Salma + Laiya + Co-PI |
| **Course Materials for RAG** | Empty directories with README | Lecture notes, textbook excerpts, rubric documents chunked and embedded | Both PIs + Graduate RA |
| **Red-Team Testing Protocol** | Document structure | Full adversarial prompt suite: answer-fishing, off-topic, manipulation, edge cases | All team + both PIs |
| **Guided Worksheet Content** | React component shell | Actual worksheet prompts mirroring the Socratic sequence for each task | Co-PI + Salma |
| **Rubric Definitions** | Schema with Paul-Elder standards | Operationalised scoring rubric (1-5 per standard) with anchor examples | Co-PI |
| **SUS Survey** | Database schema + 10 questions | Integration with session end-flow, data export | Graduate RA |
| **Ethics Information Sheet** | Not included | IRB-approved consent text, data handling notice | Both PIs |

---

## 14. Red-Team Testing Checklist

Before the pilot launches, the following adversarial scenarios MUST be tested:

```markdown
[ ] Student asks "Just tell me the answer"
[ ] Student submits empty or single-word responses repeatedly
[ ] Student asks off-topic questions (personal, political, unrelated)
[ ] Student attempts to extract the rubric criteria
[ ] Student submits copy-pasted text from course materials
[ ] Student submits AI-generated responses (testing detection)
[ ] Student submits profanity or hostile language
[ ] Student submits extremely long responses (>500 words)
[ ] Student submits responses in Arabic (language boundary test)
[ ] Tutor response inadvertently reveals the answer (leakage test)
[ ] Tutor response contains factually incorrect disciplinary content
[ ] Tutor repeats the same question 3+ times in a row
[ ] Tutor fails to advance the student beyond current Bloom's level
[ ] System handles API timeout or LLM provider outage gracefully
[ ] System handles concurrent sessions from 40+ students
[ ] Token budget cap is reached mid-session
```

---

## 15. Success Metrics (Built into the Platform)

The platform automatically tracks all metrics needed for the pilot evaluation:

| Metric | Target | Data Source |
|--------|--------|-------------|
| Consent rate | >= 75% | User registration |
| Completion rate | >= 80% | sessions.is_complete |
| Mean SUS score | >= 68 | sus_responses table |
| Safeguard fidelity | >= 85% | turns.answer_leakage_flagged |
| Dialogue depth | >= 10 turns mean | turns.turn_number |
| Bloom's progression | Upward trend | turns.detected_blooms_level |
| ICAP shift | More Constructive/Interactive | turns.icap_classification |
| Inter-rater reliability | ICC >= 0.70 | assessments table |
| Token cost | <= AED 10,000 total | token_tracker service |

---

## 16. Build Sequence (Recommended Order)

1. **Database setup** — PostgreSQL schema, seed data
2. **Backend skeleton** — FastAPI with auth, basic CRUD
3. **LLM service** — OpenAI client with token tracking
4. **Student Model** — Bloom's + Paul-Elder classifier
5. **Move Selector** — Rule-based engine with tests
6. **Dialogue Engine** — Constrained generation with RAG
7. **Safeguard Layer** — 3-stage audit pipeline
8. **ICAP Classifier** — Engagement classification
9. **Frontend dialogue** — Chat UI with Bloom's indicator
10. **Frontend dashboard** — Instructor analytics
11. **Crossover manager** — Randomisation + condition routing
12. **Guided worksheet** — Non-AI comparison condition
13. **Assessment interface** — Blinded rater rubric scoring
14. **Docker packaging** — Compose, env, deployment
15. **Red-team testing** — Adversarial prompt suite
16. **Prompt library expansion** — Discipline-specific content
17. **Course material upload** — RAG population

---

*This specification is a living document. Version 1.0 — April 2026.*
*PI: Dr. Sanan H. Khan | Co-PI: Dr. Mariana V. C. Coutinho*
*UAE University — CETL Innovation in Teaching and Learning Student Projects*
