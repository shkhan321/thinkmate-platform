import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { canSubmitWorksheet, modelModeLabel, taskActionLabel } from "./flow";
import type { AdminSummary, Health, PilotSession, PilotTask, Student, Turn } from "./types";

type View = "student" | "admin";
type Stage = "login" | "consent" | "tasks" | "active" | "complete";

export default function App() {
  const [view, setView] = useState<View>("student");
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ThinkMate Pilot</p>
          <h1>Research MVP</h1>
        </div>
        <nav className="tabs" aria-label="Main view">
          <button className={view === "student" ? "active" : ""} onClick={() => setView("student")}>
            Student
          </button>
          <button className={view === "admin" ? "active" : ""} onClick={() => setView("admin")}>
            Admin
          </button>
        </nav>
      </header>

      {health && <div className="notice">{modelModeLabel(health.model_mode)} - Database {health.database}</div>}

      {view === "student" ? <StudentPilot /> : <AdminPanel />}
    </main>
  );
}

function StudentPilot() {
  const [stage, setStage] = useState<Stage>("login");
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
      const result = await api.accessCode(accessCode);
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
    await api.completeSession(session.id);
    setStage("complete");
  }

  return (
    <section className="panel">
      {error && <div className="error">{error}</div>}
      {stage === "login" && <AccessCodeForm onSubmit={handleLogin} />}
      {stage === "consent" && <ConsentScreen student={student} onAccept={acceptConsent} />}
      {stage === "tasks" && <TaskList tasks={tasks} onStart={startTask} />}
      {stage === "active" && activeTask && session?.condition === "thinkmate" && (
        <ThinkMateChat task={activeTask} session={session} onFinish={finishSession} />
      )}
      {stage === "active" && activeTask && session?.condition === "worksheet" && (
        <Worksheet task={activeTask} session={session} onFinish={finishSession} />
      )}
      {stage === "complete" && (
        <div className="centered">
          <h2>Task submitted</h2>
          <p>Your response has been saved under your study code.</p>
          <button onClick={() => setStage("tasks")}>Return to tasks</button>
        </div>
      )}
    </section>
  );
}

function AccessCodeForm({ onSubmit }: { onSubmit: (code: string) => void }) {
  const [code, setCode] = useState("");
  return (
    <form
      className="narrow"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(code);
      }}
    >
      <h2>Enter study access code</h2>
      <p>Use the pseudonymous code provided by the research team. Do not enter your real name.</p>
      <input value={code} onChange={(event) => setCode(event.target.value)} placeholder="ENG-A-001" />
      <button disabled={!code.trim()}>Continue</button>
    </form>
  );
}

function ConsentScreen({ student, onAccept }: { student: Student | null; onAccept: () => void }) {
  return (
    <div className="narrow">
      <h2>Consent required</h2>
      <p>
        Your interaction will be logged for the ThinkMate teaching-and-learning pilot. The app stores your study code,
        course, task responses, and dialogue turns. It does not need your name for this MVP.
      </p>
      <dl className="facts">
        <dt>Course</dt>
        <dd>{student?.course}</dd>
        <dt>Sequence</dt>
        <dd>{student?.sequence}</dd>
      </dl>
      <button onClick={onAccept}>I agree and want to continue</button>
    </div>
  );
}

function TaskList({ tasks, onStart }: { tasks: PilotTask[]; onStart: (task: PilotTask) => void }) {
  return (
    <div>
      <h2>Assigned tasks</h2>
      <div className="task-grid">
        {tasks.map((task) => (
          <article className="task-row" key={task.id}>
            <div>
              <p className="eyebrow">Task {task.task_number} - {task.condition}</p>
              <h3>{task.title}</h3>
              <p>{task.scenario}</p>
            </div>
            <button onClick={() => onStart(task)}>{taskActionLabel(task.condition)}</button>
          </article>
        ))}
      </div>
    </div>
  );
}

function ThinkMateChat({ task, session, onFinish }: { task: PilotTask; session: PilotSession; onFinish: () => void }) {
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
      <aside>
        <p className="eyebrow">ThinkMate condition</p>
        <h2>{task.title}</h2>
        <p>{task.scenario}</p>
        <button className="secondary" onClick={onFinish}>Finish task</button>
      </aside>
      <section className="chat-area">
        {error && <div className="error">{error}</div>}
        <div className="messages">
          {turns.length === 0 && <p className="empty">Start by stating your claim or first reasoning step.</p>}
          {turns.map((turn) => (
            <div className={`message ${turn.role}`} key={turn.id}>
              <span>{turn.role}</span>
              <p>{turn.content}</p>
              {turn.move_type && <small>{turn.move_type} - {turn.paul_elder_target} - {turn.bloom_level}</small>}
            </div>
          ))}
        </div>
        <form className="composer" onSubmit={sendTurn}>
          <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Share your reasoning..." />
          <button disabled={busy || !input.trim()}>{busy ? "Thinking" : "Send"}</button>
        </form>
      </section>
    </div>
  );
}

function Worksheet({ task, session, onFinish }: { task: PilotTask; session: PilotSession; onFinish: () => void }) {
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const stepKeys = useMemo(() => task.worksheet_steps.map((step) => step.key), [task]);
  const ready = canSubmitWorksheet(stepKeys, responses);

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
    <div>
      <p className="eyebrow">Guided worksheet condition</p>
      <h2>{task.title}</h2>
      <p>{task.scenario}</p>
      {error && <div className="error">{error}</div>}
      <div className="worksheet">
        {task.worksheet_steps.map((step) => (
          <label key={step.key}>
            <strong>{step.label}</strong>
            <span>{step.prompt}</span>
            <textarea
              value={responses[step.key] || ""}
              onChange={(event) => setResponses((current) => ({ ...current, [step.key]: event.target.value }))}
            />
          </label>
        ))}
      </div>
      <button disabled={!ready || busy} onClick={submit}>{busy ? "Submitting" : "Submit worksheet"}</button>
    </div>
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
    <section className="panel">
      <h2>Admin export</h2>
      <p>Use this only for research-team export. Do not share the admin password with students.</p>
      {error && <div className="error">{error}</div>}
      <div className="admin-controls">
        <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Admin password" />
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
