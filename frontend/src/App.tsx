import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import {
  canSubmitWorksheet,
  conditionGuide,
  modelModeLabel,
  studentProgress,
  taskActionLabel,
  tourSteps,
  type StudentStage
} from "./flow";
import type { AdminSummary, Health, PilotSession, PilotTask, Student, Turn } from "./types";

type View = "student" | "admin";
type FinishHandler = () => Promise<void> | void;

export default function App() {
  const [view, setView] = useState<View>("student");
  const [health, setHealth] = useState<Health | null>(null);
  const [tourOpen, setTourOpen] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">UAEU Teaching and Learning Pilot</p>
          <h1>ThinkMate</h1>
          <p>Guided critical-thinking activities for students.</p>
        </div>
        <div className="top-actions">
          <button className="ghost-button" type="button" onClick={() => setTourOpen(true)}>
            Quick tour
          </button>
          <nav className="tabs" aria-label="Main view">
            <button className={view === "student" ? "active" : ""} onClick={() => setView("student")}>
              Student
            </button>
            <button className={view === "admin" ? "active" : ""} onClick={() => setView("admin")}>
              Admin
            </button>
          </nav>
        </div>
      </header>

      {health && (
        <div className="status-strip" aria-label="System status">
          <span>{modelModeLabel(health.model_mode)}</span>
          <span>Database {health.database}</span>
          <span>Consent {health.consent_version}</span>
        </div>
      )}

      {view === "student" ? <StudentPilot onOpenTour={() => setTourOpen(true)} /> : <AdminPanel />}
      {tourOpen && <QuickTour onClose={() => setTourOpen(false)} />}
    </main>
  );
}

function StudentPilot({ onOpenTour }: { onOpenTour: () => void }) {
  const [stage, setStage] = useState<StudentStage>("login");
  const [student, setStudent] = useState<Student | null>(null);
  const [tasks, setTasks] = useState<PilotTask[]>([]);
  const [activeTask, setActiveTask] = useState<PilotTask | null>(null);
  const [session, setSession] = useState<PilotSession | null>(null);
  const [error, setError] = useState("");

  async function loadTasks(studentId: string) {
    const result = await api.tasks(studentId);
    setTasks(result.tasks);
  }

  async function handleLogin(accessCode: string) {
    setError("");
    try {
      const result = await api.accessCode(accessCode.trim());
      setStudent(result);
      if (result.consent_accepted) {
        await loadTasks(result.student_id);
        setStage("tasks");
      } else {
        setStage("consent");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  async function acceptConsent() {
    if (!student) return;
    setError("");
    try {
      await api.consent(student.student_id);
      await loadTasks(student.student_id);
      setStage("tasks");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Consent failed");
    }
  }

  async function startTask(task: PilotTask) {
    if (!student) return;
    setError("");
    try {
      const newSession = await api.startSession(student.student_id, task.id);
      setActiveTask(task);
      setSession(newSession);
      setStage("active");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start task");
    }
  }

  async function finishSession() {
    if (!session) return;
    setError("");
    try {
      await api.completeSession(session.id);
      setStage("complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not finish task");
    }
  }

  return (
    <section className="student-flow">
      <StudentHeader stage={stage} student={student} onOpenTour={onOpenTour} />
      <StudentProgress stage={stage} />
      {error && <div className="error">{error}</div>}

      {stage === "login" && <AccessCodeForm onSubmit={handleLogin} onOpenTour={onOpenTour} />}
      {stage === "consent" && <ConsentScreen student={student} onAccept={acceptConsent} />}
      {stage === "tasks" && <TaskList tasks={tasks} onStart={startTask} />}
      {stage === "active" && activeTask && session?.condition === "thinkmate" && (
        <ThinkMateChat task={activeTask} session={session} onFinish={finishSession} />
      )}
      {stage === "active" && activeTask && session?.condition === "worksheet" && (
        <Worksheet task={activeTask} session={session} onFinish={finishSession} />
      )}
      {stage === "complete" && <CompletionScreen onReturn={() => setStage("tasks")} />}
    </section>
  );
}

function StudentHeader({
  stage,
  student,
  onOpenTour
}: {
  stage: StudentStage;
  student: Student | null;
  onOpenTour: () => void;
}) {
  const title =
    stage === "login"
      ? "Start your study session"
      : stage === "consent"
        ? "Review consent"
        : stage === "tasks"
          ? "Choose your assigned activity"
          : stage === "active"
            ? "Complete the activity"
            : "Your work is saved";

  const subtitle =
    stage === "login"
      ? "Use the access code given by your instructor or research team."
      : stage === "consent"
        ? "This short step explains what the pilot records before you begin."
        : stage === "tasks"
          ? "Complete the activity shown for your assigned sequence."
          : stage === "active"
            ? "Answer in your own words. You can submit when your reasoning is complete."
            : "You may return to your tasks or close this page.";

  return (
    <div className="student-hero">
      <div>
        <p className="eyebrow">Student area</p>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <div className="student-id-panel">
        <span>{student ? "Signed in as" : "Your session"}</span>
        <strong>{student ? student.access_code : "Waiting for access code"}</strong>
        {student && <small>{formatCourse(student.course)} sequence {student.sequence}</small>}
        <button className="ghost-button compact" type="button" onClick={onOpenTour}>
          View tour
        </button>
      </div>
    </div>
  );
}

function StudentProgress({ stage }: { stage: StudentStage }) {
  return (
    <ol className="progress-steps" aria-label="Student progress">
      {studentProgress(stage).map((step) => (
        <li className={step.status} key={step.label}>
          <span>{step.status === "complete" ? "Done" : step.status === "current" ? "Now" : "Next"}</span>
          <strong>{step.label}</strong>
        </li>
      ))}
    </ol>
  );
}

function QuickTour({ onClose }: { onClose: () => void }) {
  return (
    <div className="tour-backdrop" role="dialog" aria-modal="true" aria-labelledby="tour-title">
      <section className="tour-panel">
        <div className="tour-header">
          <div>
            <p className="eyebrow">Quick tour</p>
            <h2 id="tour-title">What you will do</h2>
          </div>
          <button className="ghost-button compact" type="button" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="tour-list">
          {tourSteps().map((step, index) => (
            <article key={step.title}>
              <span>{index + 1}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function AccessCodeForm({
  onSubmit,
  onOpenTour
}: {
  onSubmit: (code: string) => void;
  onOpenTour: () => void;
}) {
  const [code, setCode] = useState("");
  return (
    <div className="login-layout">
      <form
        className="entry-form"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(code);
        }}
      >
        <label htmlFor="access-code">Study access code</label>
        <input
          id="access-code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="For example: ENG-A-001"
          autoComplete="off"
        />
        <p>Use only your study code. Do not enter your real name, UAEU ID, or email address.</p>
        <button disabled={!code.trim()}>Continue</button>
      </form>

      <aside className="orientation-panel">
        <h3>Before you begin</h3>
        <ul>
          <li>This is a short research pilot activity.</li>
          <li>Your answers should be your own reasoning.</li>
          <li>The system saves responses under your study code.</li>
        </ul>
        <button className="secondary" type="button" onClick={onOpenTour}>
          See quick tour
        </button>
      </aside>
    </div>
  );
}

function ConsentScreen({ student, onAccept }: { student: Student | null; onAccept: () => void }) {
  return (
    <section className="consent-layout">
      <div>
        <h2>Consent to continue</h2>
        <p>
          ThinkMate will save your study code, course, activity responses, and dialogue or worksheet entries. The pilot
          does not ask for your name on this platform.
        </p>
        <ul className="plain-list">
          <li>Take part only if you agree to the pilot activity.</li>
          <li>Write your own thinking, not personal or private information.</li>
          <li>You can ask the research team if anything is unclear before starting.</li>
        </ul>
        <button onClick={onAccept}>I agree and want to continue</button>
      </div>
      <dl className="facts">
        <dt>Course</dt>
        <dd>{student ? formatCourse(student.course) : "Not loaded"}</dd>
        <dt>Sequence</dt>
        <dd>{student?.sequence || "Not loaded"}</dd>
        <dt>Access code</dt>
        <dd>{student?.access_code || "Not loaded"}</dd>
      </dl>
    </section>
  );
}

function TaskList({ tasks, onStart }: { tasks: PilotTask[]; onStart: (task: PilotTask) => void }) {
  return (
    <section className="task-section">
      <div className="section-heading">
        <div>
          <h2>Your activities</h2>
          <p>Open the activity assigned to you. The platform will save your work after you submit.</p>
        </div>
        <span>{tasks.length} assigned</span>
      </div>
      <div className="task-grid">
        {tasks.map((task) => (
          <article className="task-row" key={task.id}>
            <div>
              <p className="eyebrow">Task {task.task_number}</p>
              <h3>{task.title}</h3>
              <p>{task.scenario}</p>
              <p className="condition-note">{conditionGuide(task.condition)}</p>
            </div>
            <div className="task-action">
              <span>{task.condition === "thinkmate" ? "Discussion" : "Worksheet"}</span>
              <button onClick={() => onStart(task)}>{taskActionLabel(task.condition)}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ThinkMateChat({ task, session, onFinish }: { task: PilotTask; session: PilotSession; onFinish: FinishHandler }) {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function sendTurn(event: FormEvent) {
    event.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await api.dialogueTurn(session.id, input);
      setTurns((current) => [...current, response.student_turn, response.tutor_turn]);
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send turn");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="workspace">
      <aside className="activity-brief">
        <p className="eyebrow">ThinkMate discussion</p>
        <h2>{task.title}</h2>
        <p>{task.scenario}</p>
        <div className="brief-box">
          <strong>How to answer</strong>
          <ul>
            <li>Start with your claim or decision.</li>
            <li>Explain the evidence or assumption behind it.</li>
            <li>Answer ThinkMate's question before moving on.</li>
          </ul>
        </div>
        <button className="secondary" onClick={() => void onFinish()}>
          Finish and save
        </button>
      </aside>

      <section className="chat-area">
        <div className="chat-heading">
          <div>
            <h2>Reasoning chat</h2>
            <p>ThinkMate will ask questions. It will not give you the final answer.</p>
          </div>
          <span>{turns.length === 0 ? "Not started" : `${Math.ceil(turns.length / 2)} exchange(s)`}</span>
        </div>
        {error && <div className="error">{error}</div>}
        <div className="messages">
          {turns.length === 0 && (
            <div className="empty-state">
              <strong>Start with one clear sentence.</strong>
              <p>Example: "My claim is that the safer design is better because..."</p>
            </div>
          )}
          {turns.map((turn) => (
            <div className={`message ${turn.role}`} key={turn.id}>
              <span>{turn.role === "tutor" ? "ThinkMate" : "You"}</span>
              <p>{turn.content}</p>
              {turn.move_type && <small>{turn.move_type} | {turn.paul_elder_target} | {turn.bloom_level}</small>}
            </div>
          ))}
        </div>
        <form className="composer" onSubmit={sendTurn}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Type your reasoning here..."
          />
          <button disabled={busy || !input.trim()}>{busy ? "Thinking..." : "Send"}</button>
        </form>
      </section>
    </div>
  );
}

function Worksheet({ task, session, onFinish }: { task: PilotTask; session: PilotSession; onFinish: FinishHandler }) {
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const stepKeys = useMemo(() => task.worksheet_steps.map((step) => step.key), [task]);
  const ready = canSubmitWorksheet(stepKeys, responses);
  const completedCount = stepKeys.filter((key) => (responses[key] || "").trim().length > 0).length;

  async function submit() {
    setBusy(true);
    setError("");
    try {
      for (const step of task.worksheet_steps) {
        await api.worksheetResponse(session.id, step.key, step.prompt, responses[step.key]);
      }
      await onFinish();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit worksheet");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="workspace">
      <aside className="activity-brief">
        <p className="eyebrow">Guided worksheet</p>
        <h2>{task.title}</h2>
        <p>{task.scenario}</p>
        <div className="brief-box">
          <strong>What to do</strong>
          <p>Complete each box in your own words. You can submit when all boxes have an answer.</p>
        </div>
        <span className="completion-meter">{completedCount} of {stepKeys.length} boxes complete</span>
      </aside>

      <section className="worksheet-area">
        <div className="section-heading">
          <div>
            <h2>Worksheet responses</h2>
            <p>{conditionGuide("worksheet")}</p>
          </div>
        </div>
        {error && <div className="error">{error}</div>}
        <div className="worksheet">
          {task.worksheet_steps.map((step, index) => (
            <label key={step.key}>
              <strong>Step {index + 1}: {step.label}</strong>
              <span>{step.prompt}</span>
              <textarea
                value={responses[step.key] || ""}
                onChange={(event) => setResponses((current) => ({ ...current, [step.key]: event.target.value }))}
              />
            </label>
          ))}
        </div>
        <button disabled={!ready || busy} onClick={submit}>{busy ? "Submitting..." : "Submit worksheet"}</button>
      </section>
    </div>
  );
}

function CompletionScreen({ onReturn }: { onReturn: () => void }) {
  return (
    <section className="completion-panel">
      <span>Saved</span>
      <h2>Your activity has been submitted</h2>
      <p>Your response is stored under your study code. You can return to the activity list if another task is assigned.</p>
      <button onClick={onReturn}>Return to activities</button>
    </section>
  );
}

function AdminPanel() {
  const [password, setPassword] = useState("");
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [exportText, setExportText] = useState("");
  const [blinded, setBlinded] = useState(true);
  const [error, setError] = useState("");

  async function loadSummary() {
    setError("");
    try {
      setSummary(await api.adminSummary(password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Admin request failed");
    }
  }

  async function exportData(format: "json" | "csv") {
    setError("");
    try {
      if (format === "json") {
        const data = await api.adminExportJson(password, blinded);
        setExportText(JSON.stringify(data, null, 2));
      } else {
        setExportText(await api.adminExportCsv(password, blinded));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  }

  return (
    <section className="admin-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Research team only</p>
          <h2>Admin export</h2>
          <p>Use this area for pilot monitoring and data export. Do not share the admin password with students.</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="admin-controls">
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Admin password"
        />
        <label className="check">
          <input type="checkbox" checked={blinded} onChange={(event) => setBlinded(event.target.checked)} />
          Blinded export
        </label>
        <button onClick={loadSummary}>Load summary</button>
        <button onClick={() => exportData("json")}>Export JSON</button>
        <button onClick={() => exportData("csv")}>Export CSV</button>
      </div>
      {summary && (
        <div className="stats">
          <div><b>{summary.students}</b><span>Students</span></div>
          <div><b>{summary.sessions}</b><span>Sessions</span></div>
          <div><b>{summary.turns}</b><span>Turns</span></div>
          <div><b>{summary.worksheet_responses}</b><span>Worksheet rows</span></div>
        </div>
      )}
      {exportText && <textarea className="export-box" value={exportText} readOnly />}
    </section>
  );
}

function formatCourse(course: string): string {
  return course.charAt(0).toUpperCase() + course.slice(1);
}
