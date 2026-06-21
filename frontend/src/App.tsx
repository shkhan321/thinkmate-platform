import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "./api";
import {
  COURSES,
  conditionTitle,
  conditionGuide,
  courseCode,
  courseLabel,
  firstName,
  modelModeLabel,
  projectDraftKey,
  studentProgress,
  taskActionLabel,
  type StudentStage
} from "./flow";
import type { Health, PilotSession, PilotTask, Student } from "./types";
import { ThinkMateChat } from "./components/Chat";
import { Worksheet } from "./components/Worksheet";
import { AdminPanel } from "./components/Admin";
import { ProjectIntake } from "./components/ProjectIntake";
import { Callout, QuickTour, Stepper, Wordmark } from "./components/ui";
import {
  ArrowRightIcon,
  ChatIcon,
  CheckIcon,
  ClipboardIcon,
  CompassIcon,
  CopyIcon,
  LightbulbIcon,
  ShieldIcon,
  SparkIcon,
  StarIcon
} from "./components/icons";

type View = "student" | "admin";

const STORAGE_KEY = "thinkmate.student";

export default function App() {
  const [view, setView] = useState<View>("student");
  const [health, setHealth] = useState<Health | null>(null);
  const [tourOpen, setTourOpen] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  // The research/admin area is not advertised to students. The team reaches it
  // via the URL hash (e.g. .../#admin), still behind the admin password.
  useEffect(() => {
    function applyHash() {
      const hash = window.location.hash.toLowerCase();
      if (hash === "#admin" || hash === "#research") setView("admin");
    }
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only rounded-xl bg-brand-600 px-4 py-2 font-semibold text-white focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50"
      >
        Skip to main content
      </a>
      <TopBar view={view} setView={setView} health={health} onOpenTour={() => setTourOpen(true)} />

      <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 sm:py-10">
        {view === "student" ? (
          <StudentExperience onOpenTour={() => setTourOpen(true)} />
        ) : (
          <AdminPanel />
        )}
      </main>

      <SiteFooter view={view} setView={setView} />
      {tourOpen && <QuickTour onClose={() => setTourOpen(false)} />}
    </div>
  );
}

function TopBar({
  view,
  setView,
  health,
  onOpenTour
}: {
  view: View;
  setView: (view: View) => void;
  health: Health | null;
  onOpenTour: () => void;
}) {
  const online = health ? health.model_mode !== "demo" : false;
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white shadow-sm">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <button type="button" onClick={() => setView("student")} className="rounded-xl">
          <Wordmark />
        </button>
        <div className="flex items-center gap-2">
          {health && (
            <span
              className={`hidden items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold sm:inline-flex ${
                online ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
              }`}
              title={`Database ${health.database}`}
            >
              <span className={`h-2 w-2 rounded-full ${online ? "bg-emerald-500" : "bg-amber-500"}`} />
              {modelModeLabel(health.model_mode)}
            </span>
          )}
          {view === "student" ? (
            <button type="button" className="tm-btn-ghost" onClick={onOpenTour}>
              <CompassIcon className="h-4 w-4" /> Tour
            </button>
          ) : (
            <button type="button" className="tm-btn-ghost" onClick={() => setView("student")}>
              Back to student
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

function SiteFooter({ view, setView }: { view: View; setView: (view: View) => void }) {
  return (
    <footer className="border-t border-slate-200 px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-5xl flex-col items-center justify-between gap-2 text-center text-xs text-slate-400 sm:flex-row sm:text-left">
        <p>ThinkMate · UAE University Teaching &amp; Learning pilot</p>
        {view === "admin" && (
          <button
            type="button"
            className="font-semibold text-brand-600 hover:text-brand-700"
            onClick={() => setView("student")}
          >
            ← Back to student view
          </button>
        )}
      </div>
    </footer>
  );
}

function StudentExperience({ onOpenTour }: { onOpenTour: () => void }) {
  const [stage, setStage] = useState<StudentStage>("login");
  const [student, setStudent] = useState<Student | null>(null);
  const [tasks, setTasks] = useState<PilotTask[]>([]);
  const [activeTask, setActiveTask] = useState<PilotTask | null>(null);
  const [session, setSession] = useState<PilotSession | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const stageRef = useRef<StudentStage>(stage);
  const studentRef = useRef<Student | null>(student);
  useEffect(() => {
    stageRef.current = stage;
  }, [stage]);
  useEffect(() => {
    studentRef.current = student;
  }, [student]);

  // Map the browser Back button to an in-app "back to activities" while a
  // student is in an activity, so Back never leaves the app to a blank page.
  useEffect(() => {
    if (stage === "active") {
      try {
        window.history.pushState({ tm: "activity" }, "");
      } catch {
        /* history unavailable: fall back to default behaviour */
      }
    }
  }, [stage]);

  useEffect(() => {
    function onPopState() {
      const current = stageRef.current;
      if (current === "active" || current === "wrapup" || current === "complete") {
        try {
          window.history.pushState({ tm: "trap" }, "");
        } catch {
          /* ignore */
        }
        setActiveTask(null);
        setSession(null);
        setError("");
        setStage("tasks");
        const sid = studentRef.current?.student_id;
        if (sid) api.tasks(sid).then((result) => setTasks(result.tasks)).catch(() => undefined);
      }
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  // Resume a saved session on reload so students never lose their place.
  useEffect(() => {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return;
    let saved: Student;
    try {
      saved = JSON.parse(raw) as Student;
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }
    setStudent(saved);
    void resume(saved);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function persist(value: Student) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  }

  async function loadTasks(studentId: string) {
    const result = await api.tasks(studentId);
    setTasks(result.tasks);
  }

  // Route a signed-in student to the right next step: consent -> project -> tasks.
  async function routeEntry(s: Student) {
    if (!s.consent_accepted) {
      setStage("consent");
      return;
    }
    if (!s.project_title) {
      setStage("project");
      return;
    }
    await loadTasks(s.student_id);
    setStage("tasks");
  }

  async function resume(saved: Student) {
    try {
      await routeEntry(saved);
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      setStudent(null);
      setStage("login");
    }
  }

  async function handleStart(name: string, course: string) {
    if (pending) return;
    setError("");
    setPending(true);
    try {
      const result = await api.start(name, course);
      setStudent(result);
      persist(result);
      await routeEntry(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign you in. Please try again.");
    } finally {
      setPending(false);
    }
  }

  async function acceptConsent() {
    if (!student || pending) return;
    setError("");
    setPending(true);
    try {
      await api.consent(student.student_id);
      const updated = { ...student, consent_accepted: true };
      setStudent(updated);
      persist(updated);
      await routeEntry(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record your agreement. Please try again.");
    } finally {
      setPending(false);
    }
  }

  async function saveProjectInfo(title: string, goal: string) {
    if (!student || pending) return;
    setError("");
    setPending(true);
    try {
      const result = await api.saveProject(student.student_id, title, goal);
      const updated = { ...student, project_title: result.project_title, project_goal: result.project_goal };
      setStudent(updated);
      persist(updated);
      const draftKey = projectDraftKey(student.student_id);
      if (draftKey) window.localStorage.removeItem(draftKey);
      await loadTasks(student.student_id);
      setStage("tasks");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your project. Please try again.");
    } finally {
      setPending(false);
    }
  }

  async function startTask(task: PilotTask) {
    if (!student || pending) return;
    setError("");
    setPending(true);
    try {
      const newSession = await api.startSession(student.student_id, task.id);
      setActiveTask(task);
      setSession(newSession);
      setStage("active");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start this activity. Please try again.");
    } finally {
      setPending(false);
    }
  }

  // Worksheet finishes straight away (its reflection box is the student's answer).
  // A ThinkMate chat goes to a wrap-up step where the student writes their own
  // improved answer before finishing.
  async function finishSession() {
    if (!session) return;
    if (session.condition === "thinkmate") {
      setError("");
      setStage("wrapup");
      return;
    }
    await completeAndReturn();
  }

  async function completeAndReturn() {
    if (!session) return;
    setError("");
    try {
      await api.completeSession(session.id);
      if (student) await loadTasks(student.student_id);
      setStage("complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your work. Please try again.");
    }
  }

  async function finalizeWithAnswer(answer: string) {
    if (!session || pending) return;
    setError("");
    setPending(true);
    try {
      await api.saveAnswer(session.id, answer);
      await api.completeSession(session.id);
      if (student) await loadTasks(student.student_id);
      setStage("complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your answer. Please try again.");
    } finally {
      setPending(false);
    }
  }

  function finalizeSkip() {
    void completeAndReturn();
  }

  async function backToActivities() {
    setActiveTask(null);
    setSession(null);
    setError("");
    if (student) {
      try {
        await loadTasks(student.student_id);
      } catch {
        /* keep showing the cached task list if the refresh fails */
      }
    }
    setStage("tasks");
  }

  function signOut() {
    window.localStorage.removeItem(STORAGE_KEY);
    setStudent(null);
    setTasks([]);
    setActiveTask(null);
    setSession(null);
    setError("");
    setStage("login");
  }

  if (stage === "login") {
    return <SignIn onStart={handleStart} onOpenTour={onOpenTour} error={error} pending={pending} />;
  }

  return (
    <div className="space-y-6">
      <SignedInBar student={student} stage={stage} onSignOut={signOut} />
      {error && stage !== "active" && <Callout>{error}</Callout>}

      {stage === "consent" && (
        <ConsentScreen student={student} onAccept={acceptConsent} onDecline={signOut} pending={pending} />
      )}
      {stage === "project" && (
        <ProjectIntake student={student} onSave={saveProjectInfo} error={error} pending={pending} />
      )}
      {stage === "tasks" && (
        <TaskList
          student={student}
          tasks={tasks}
          onStart={startTask}
          onEditProject={() => setStage("project")}
          pending={pending}
        />
      )}
      {stage === "active" && activeTask && session?.condition === "thinkmate" && (
        <ThinkMateChat
          task={activeTask}
          session={session}
          projectTitle={student?.project_title}
          projectGoal={student?.project_goal}
          onFinish={finishSession}
          onBack={backToActivities}
        />
      )}
      {stage === "active" && activeTask && session?.condition === "worksheet" && (
        <Worksheet
          task={activeTask}
          session={session}
          projectTitle={student?.project_title}
          projectGoal={student?.project_goal}
          onFinish={finishSession}
          onBack={backToActivities}
        />
      )}
      {stage === "wrapup" && (
        <WrapUp onSave={finalizeWithAnswer} onSkip={finalizeSkip} pending={pending} error={error} />
      )}
      {stage === "complete" && (
        <CompletionScreen session={session} tasks={tasks} onReturn={() => setStage("tasks")} />
      )}
    </div>
  );
}

function SignedInBar({
  student,
  stage,
  onSignOut
}: {
  student: Student | null;
  stage: StudentStage;
  onSignOut: () => void;
}) {
  if (!student) return null;
  const steps = studentProgress(stage);
  const currentNum = steps.findIndex((step) => step.status === "current") + 1;
  return (
    <div className="tm-card flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-50 text-base font-extrabold text-brand-700">
          {initials(student.display_name)}
        </span>
        <div className="leading-tight">
          <p className="font-bold text-slate-900">{student.display_name || "Student"}</p>
          <p className="text-xs text-slate-500">
            {courseLabel(student.course)} · ID {student.access_code}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {currentNum > 0 && (
          <span className="text-xs font-semibold text-slate-500 sm:hidden">
            Step {currentNum} of {steps.length}
          </span>
        )}
        <div className="hidden sm:block">
          <Stepper stage={stage} />
        </div>
        <button type="button" className="tm-btn-ghost shrink-0" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </div>
  );
}

function SignIn({
  onStart,
  onOpenTour,
  error,
  pending
}: {
  onStart: (name: string, course: string) => void;
  onOpenTour: () => void;
  error: string;
  pending: boolean;
}) {
  const [name, setName] = useState("");
  const [course, setCourse] = useState("");
  const ready = name.trim().length > 0 && course.length > 0;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (ready) onStart(name, course);
  }

  return (
    <div className="tm-rise grid items-center gap-8 lg:grid-cols-[1.05fr_1fr]">
      <section className="order-2 lg:order-1">
        <span className="tm-chip bg-white/80 text-brand-700 shadow-sm">
          <SparkIcon className="h-3.5 w-3.5" /> UAE University · Teaching &amp; Learning
        </span>
        <h1 className="mt-4 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl">
          Think it through with{" "}
          <span className="bg-gradient-to-r from-brand-600 to-accent-500 bg-clip-text text-transparent">
            ThinkMate
          </span>
        </h1>
        <p className="mt-4 max-w-md text-lg leading-relaxed text-slate-600">
          Bring <strong>your own</strong> capstone project. ThinkMate asks sharp questions about it to
          strengthen your reasoning — it never just hands you the answer.
        </p>

        <ul className="mt-6 space-y-3">
          <Feature icon={<ChatIcon className="h-5 w-5" />} title="About your real project">
            Tell it what you're building or studying. Every question is about your work.
          </Feature>
          <Feature icon={<LightbulbIcon className="h-5 w-5" />} title="Builds your thinking, on a map">
            Watch your reasoning grow step by step: claim, evidence, assumptions, counter-views.
          </Feature>
          <Feature icon={<ShieldIcon className="h-5 w-5" />} title="Sign in with just your name">
            No password. Your work is saved automatically.
          </Feature>
        </ul>

        <div className="mt-6 max-w-md rounded-2xl border border-brand-100 bg-white/70 p-4">
          <p className="text-sm font-bold text-slate-800">Why not just use ChatGPT?</p>
          <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="font-semibold text-slate-500">ChatGPT</p>
              <p className="mt-0.5 text-slate-600">Gives you the answer. You stop thinking.</p>
            </div>
            <div className="rounded-xl bg-brand-50 p-3">
              <p className="font-semibold text-brand-700">ThinkMate</p>
              <p className="mt-0.5 text-slate-700">Makes you find it. Your thinking gets stronger.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="order-1 lg:order-2">
        <form className="tm-card p-6 sm:p-8" onSubmit={submit}>
          <h2 className="text-xl font-extrabold text-slate-900">Let&rsquo;s get started</h2>
          <p className="mt-1 text-sm text-slate-600">Sign in with your name to begin.</p>

          {error && (
            <div className="mt-4">
              <Callout>{error}</Callout>
            </div>
          )}

          <label htmlFor="student-name" className="mt-5 block text-sm font-semibold text-slate-700">
            Your name
          </label>
          <input
            id="student-name"
            className="tm-input mt-1.5"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Aisha Khalifa"
            autoComplete="name"
            maxLength={80}
          />

          <p className="mt-5 text-sm font-semibold text-slate-700">Your course</p>
          <div className="mt-1.5 grid gap-2.5 sm:grid-cols-2">
            {COURSES.map((item) => {
              const selected = course === item.value;
              return (
                <button
                  type="button"
                  key={item.value}
                  onClick={() => setCourse(item.value)}
                  aria-pressed={selected}
                  className={`rounded-2xl border p-4 text-left transition ${
                    selected
                      ? "border-brand-500 bg-brand-50 ring-2 ring-brand-200"
                      : "border-slate-200 bg-white hover:border-brand-300"
                  }`}
                >
                  <span className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">{item.label}</span>
                    {selected && <CheckIcon className="h-4 w-4 text-brand-600" />}
                  </span>
                  <span className="mt-0.5 block text-xs font-semibold text-brand-600">{item.code}</span>
                  <span className="mt-1 block text-xs text-slate-500">{item.blurb}</span>
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-slate-400">
            ThinkMate is currently running for these two pilot courses. More may be added later.
          </p>

          <button className="tm-btn-primary mt-6 w-full" disabled={!ready || pending}>
            {pending ? "Signing you in…" : <>Continue <ArrowRightIcon className="h-5 w-5" /></>}
          </button>

          <button
            type="button"
            onClick={onOpenTour}
            className="mt-3 w-full text-center text-sm font-semibold text-slate-500 hover:text-brand-600"
          >
            New here? Take the quick tour
          </button>
        </form>
      </section>
    </div>
  );
}

function Feature({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white text-brand-600 shadow-sm">
        {icon}
      </span>
      <div>
        <p className="font-bold text-slate-900">{title}</p>
        <p className="text-sm text-slate-600">{children}</p>
      </div>
    </li>
  );
}

function ConsentScreen({
  student,
  onAccept,
  onDecline,
  pending
}: {
  student: Student | null;
  onAccept: () => void;
  onDecline: () => void;
  pending: boolean;
}) {
  const [declined, setDeclined] = useState(false);
  return (
    <section className="tm-card tm-rise mx-auto max-w-2xl p-6 sm:p-8">
      <span className="tm-chip bg-brand-50 text-brand-700">
        <ShieldIcon className="h-3.5 w-3.5" /> Before you begin
      </span>
      <h2 className="mt-3 text-2xl font-extrabold text-slate-900">A quick note, then you&rsquo;re in</h2>
      <p className="mt-2 text-slate-600">
        This is a short university learning activity. ThinkMate saves your activity answers and the
        discussion or worksheet you complete, so your reasoning can be reviewed later by the research team.
      </p>

      <ul className="mt-5 space-y-2.5">
        {[
          "Take part only if you are happy to join this activity.",
          "Write your own thinking — there are no trick questions.",
          "You can stop at any time, and you can ask the team if anything is unclear."
        ].map((line) => (
          <li key={line} className="flex items-start gap-2.5 text-slate-700">
            <CheckIcon className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
            <span>{line}</span>
          </li>
        ))}
      </ul>

      {student && (
        <dl className="mt-6 grid grid-cols-2 gap-3 rounded-2xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-semibold text-slate-500">Course</dt>
            <dd className="font-bold text-slate-900">{courseLabel(student.course)}</dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">Your saved-work code</dt>
            <dd className="font-bold text-slate-900">{student.access_code}</dd>
          </div>
        </dl>
      )}

      {declined ? (
        <div className="mt-6 rounded-2xl bg-slate-50 p-4">
          <p className="text-sm text-slate-700">
            That&rsquo;s completely fine — taking part is your choice. You can simply close this page; nothing is
            saved. If you change your mind, sign in again any time.
          </p>
          <button className="tm-btn-ghost mt-3" type="button" onClick={onDecline}>
            Back to start
          </button>
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:items-center">
          <button className="tm-btn-primary w-full sm:w-auto" onClick={onAccept} disabled={pending}>
            {pending ? "One moment…" : <>I agree — let&rsquo;s continue <ArrowRightIcon className="h-5 w-5" /></>}
          </button>
          <button
            className="text-sm font-semibold text-slate-500 hover:text-brand-600 sm:ml-2"
            type="button"
            onClick={() => setDeclined(true)}
          >
            I&rsquo;d rather not take part
          </button>
        </div>
      )}
    </section>
  );
}

function TaskList({
  student,
  tasks,
  onStart,
  onEditProject,
  pending
}: {
  student: Student | null;
  tasks: PilotTask[];
  onStart: (task: PilotTask) => void;
  onEditProject: () => void;
  pending: boolean;
}) {
  const remaining = tasks.filter((task) => !task.completed).length;
  const firstIncompleteId = tasks.find((task) => !task.completed)?.id;
  return (
    <section className="tm-rise space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900">
            Hi {firstName(student?.display_name)} 👋
          </h2>
          <p className="mt-1 text-slate-600">
            {remaining > 0
              ? "You have two short activities about your own project. They use different styles on purpose — one is a chat with ThinkMate, the other a self-guided worksheet. Start with Activity 1."
              : "You have completed all your activities. Thank you!"}
          </p>
        </div>
        {student && (
          <span className="hidden shrink-0 text-xs font-semibold text-slate-400 sm:block">
            {courseCode(student.course)}
          </span>
        )}
      </div>

      {student?.project_title && (
        <div className="tm-card flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wide text-brand-600">Your project</p>
            <p className="truncate font-semibold text-slate-800">{student.project_title}</p>
          </div>
          <button type="button" className="tm-btn-ghost shrink-0 !px-3 !py-1.5 text-xs" onClick={onEditProject}>
            Edit project
          </button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {tasks.map((task) => {
          const isChat = task.condition === "thinkmate";
          return (
            <article key={task.id} className="tm-card flex flex-col p-5">
              <div className="flex items-center justify-between">
                <span
                  className={`tm-chip ${
                    isChat ? "bg-brand-50 text-brand-700" : "bg-accent-50 text-accent-600"
                  }`}
                >
                  {isChat ? <ChatIcon className="h-3.5 w-3.5" /> : <ClipboardIcon className="h-3.5 w-3.5" />}
                  {conditionTitle(task.condition)}
                </span>
                {task.completed ? (
                  <span className="tm-chip bg-emerald-50 text-emerald-700">
                    <CheckIcon className="h-3.5 w-3.5" /> Done
                  </span>
                ) : task.in_progress ? (
                  <span className="tm-chip bg-amber-50 text-amber-700">In progress</span>
                ) : (
                  task.id === firstIncompleteId && (
                    <span className="tm-chip bg-brand-600 text-white">Start here</span>
                  )
                )}
              </div>

              <p className="mt-3 text-xs font-bold uppercase tracking-wide text-slate-400">
                Activity {task.task_number}
              </p>
              <h3 className="mt-0.5 text-lg font-extrabold text-slate-900">{task.title}</h3>
              <p className="mt-1 flex-1 text-sm leading-relaxed text-slate-600">{task.scenario}</p>
              <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
                {conditionGuide(task.condition)}
              </p>

              <button
                className={task.completed ? "tm-btn-ghost mt-4 w-full" : "tm-btn-primary mt-4 w-full"}
                onClick={() => onStart(task)}
                disabled={pending}
              >
                {pending
                  ? "Opening…"
                  : task.completed
                    ? "Open again"
                    : task.in_progress
                      ? task.condition === "thinkmate"
                        ? "Continue discussion"
                        : "Continue worksheet"
                      : taskActionLabel(task.condition)}
                {!task.completed && !pending && <ArrowRightIcon className="h-5 w-5" />}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function WrapUp({
  onSave,
  onSkip,
  pending,
  error
}: {
  onSave: (answer: string) => void;
  onSkip: () => void;
  pending: boolean;
  error: string;
}) {
  const [answer, setAnswer] = useState("");
  const ready = answer.trim().length > 0;
  return (
    <section className="tm-card tm-rise mx-auto max-w-2xl p-6 sm:p-8">
      <span className="tm-chip bg-brand-50 text-brand-700">
        <CheckIcon className="h-3.5 w-3.5" /> Last step
      </span>
      <h2 className="mt-3 text-2xl font-extrabold text-slate-900">Now, write your answer</h2>
      <p className="mt-2 text-slate-600">
        You&rsquo;ve thought it through with ThinkMate. In your own words, what&rsquo;s your answer or
        decision now? This is the part you keep — writing it yourself is how it sticks.
      </p>

      {error && (
        <div className="mt-4">
          <Callout>{error}</Callout>
        </div>
      )}

      <textarea
        className="tm-input mt-4 min-h-[7rem] resize-y"
        value={answer}
        onChange={(event) => setAnswer(event.target.value)}
        placeholder="In one or two sentences: my answer is… because…"
        autoFocus
      />

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <button className="tm-btn-primary" onClick={() => ready && onSave(answer)} disabled={!ready || pending}>
          {pending ? "Saving…" : <>Save &amp; finish <ArrowRightIcon className="h-5 w-5" /></>}
        </button>
        <button className="tm-btn-ghost" onClick={onSkip} disabled={pending} type="button">
          Finish without writing
        </button>
      </div>
    </section>
  );
}

function Feedback({ studentId }: { studentId: string }) {
  const storageKey = `thinkmate.feedback.${studentId}`;
  const [given, setGiven] = useState(() => {
    try {
      return window.localStorage.getItem(storageKey) === "1";
    } catch {
      return false;
    }
  });
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    if (!rating || busy) return;
    setBusy(true);
    try {
      await api.submitFeedback(studentId, rating, comment);
      try {
        window.localStorage.setItem(storageKey, "1");
      } catch {
        /* private mode: still hide the form for this view */
      }
      setGiven(true);
    } catch {
      /* keep the form so the student can retry */
    } finally {
      setBusy(false);
    }
  }

  if (given) {
    return (
      <div className="tm-card p-5 text-center">
        <p className="text-sm font-semibold text-slate-700">Thanks for your feedback 🙏</p>
      </div>
    );
  }

  return (
    <div className="tm-card p-5">
      <p className="text-sm font-extrabold text-slate-900">How was it?</p>
      <p className="mt-0.5 text-xs text-slate-500">Your rating helps us improve ThinkMate — it&rsquo;s optional.</p>
      <div className="mt-3 flex items-center gap-1" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            aria-label={`${n} star${n > 1 ? "s" : ""}`}
            aria-pressed={rating === n}
            onClick={() => setRating(n)}
            onMouseEnter={() => setHover(n)}
            className="rounded-lg p-0.5 focus-visible:ring-2 focus-visible:ring-brand-300"
          >
            <StarIcon className={`h-7 w-7 transition ${(hover || rating) >= n ? "text-amber-400" : "text-slate-200"}`} />
          </button>
        ))}
      </div>
      <textarea
        className="tm-input mt-3 min-h-[3.5rem] resize-y"
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder="Anything you'd like to tell us? (optional)"
        maxLength={1000}
      />
      <button className="tm-btn-primary mt-3" onClick={send} disabled={!rating || busy}>
        {busy ? "Sending…" : "Send feedback"}
      </button>
    </div>
  );
}

function CompletionScreen({
  session,
  tasks,
  onReturn
}: {
  session: PilotSession | null;
  tasks: PilotTask[];
  onReturn: () => void;
}) {
  const remaining = tasks.filter((task) => !task.completed).length;
  const [summary, setSummary] = useState("");
  const [kind, setKind] = useState<string>("");
  const [finalAnswer, setFinalAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!session) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    setFailed(false);
    api
      .sessionSummary(session.id)
      .then((result) => {
        if (!active) return;
        setSummary(result.summary);
        setKind(result.kind);
        setFinalAnswer(result.final_answer);
      })
      .catch(() => active && setFailed(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [session]);

  const clipboardText = finalAnswer ? `My answer: ${finalAnswer}\n\n${summary}` : summary;

  async function copy() {
    try {
      await navigator.clipboard.writeText(clipboardText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  const isAi = kind === "ai";
  const takeawayTitle = isAi ? "Your thinking brief" : "Your worksheet answers";
  const takeawayHint = isAi
    ? "A short summary of your own reasoning. Paste it into your capstone notes or report."
    : "Your saved answers, ready to copy into your capstone notes.";

  return (
    <section className="tm-rise mx-auto max-w-xl space-y-4">
      <div className="tm-card p-7 text-center">
        <span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-50 text-emerald-600">
          <CheckIcon className="h-8 w-8" />
        </span>
        <h2 className="mt-4 text-2xl font-extrabold text-slate-900">Nicely done — your work is saved</h2>
        <p className="mt-2 text-slate-600">Here is something to take with you.</p>
      </div>

      {finalAnswer && (
        <div className="tm-card border-2 border-brand-200 p-5 text-left">
          <p className="flex items-center gap-1.5 text-sm font-extrabold text-brand-700">
            <CheckIcon className="h-4 w-4" /> Your answer
          </p>
          <p className="mt-2 whitespace-pre-wrap text-base font-medium leading-relaxed text-slate-800">
            {finalAnswer}
          </p>
        </div>
      )}

      <div className="tm-card p-5 text-left">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="flex items-center gap-1.5 text-sm font-extrabold text-slate-900">
              <LightbulbIcon className="h-4 w-4 text-accent-600" /> {takeawayTitle}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">{takeawayHint}</p>
          </div>
          {!loading && !failed && summary && (
            <button type="button" className="tm-btn-ghost shrink-0 !px-3 !py-1.5 text-xs" onClick={copy}>
              <CopyIcon className="h-4 w-4" /> {copied ? "Copied!" : "Copy"}
            </button>
          )}
        </div>

        <div className="mt-3 rounded-2xl bg-slate-50 p-4">
          {loading ? (
            <p className="flex items-center gap-2 text-sm text-slate-500">
              <SparkIcon className="h-4 w-4 animate-pulse text-brand-500" />
              {isAi || !kind ? "Putting together your thinking brief…" : "Loading your answers…"}
            </p>
          ) : failed ? (
            <p className="text-sm text-slate-600">
              We couldn&rsquo;t build your takeaway just now — but your work is safely saved. You can scroll back
              over your answers any time.
            </p>
          ) : (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{summary}</p>
          )}
        </div>
      </div>

      {session && <Feedback studentId={session.student_id} />}

      <div className="tm-card p-5 text-center">
        <p className="text-sm text-slate-600">
          {remaining > 0
            ? "You have one more activity waiting whenever you are ready."
            : "That was your last activity. Thank you for taking part!"}
        </p>
        <button className="tm-btn-primary mt-3" onClick={onReturn}>
          {remaining > 0 ? "Back to my activities" : "View my activities"}
        </button>
      </div>
    </section>
  );
}

function initials(name?: string | null): string {
  if (!name) return "🙂";
  const parts = name.trim().split(/\s+/);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "🙂";
}
