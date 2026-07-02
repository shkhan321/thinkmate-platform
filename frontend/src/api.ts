import type {
  AdminSummary,
  Health,
  PilotSession,
  PilotTask,
  Student,
  Turn
} from "./types";

export function resolveApiBase(configuredUrl = import.meta.env.VITE_API_URL): string {
  return (configuredUrl || "").replace(/\/$/, "");
}

const API_BASE = resolveApiBase();

// Hard cap so a hung/slow model can never pin a request forever — the student
// gets a friendly error and can retry instead of staring at a spinner.
const REQUEST_TIMEOUT_MS = 90000;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("That took too long. Please check your connection and try again.");
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // keep status text
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),
  start: (name: string, course: string, forceNew = false) =>
    request<Student>("/api/auth/start", {
      method: "POST",
      body: JSON.stringify({ name, course, force_new: forceNew })
    }),
  accessCode: (accessCode: string) =>
    request<Student>("/api/auth/access-code", {
      method: "POST",
      body: JSON.stringify({ access_code: accessCode })
    }),
  consent: (studentId: string, accepted = true) =>
    request<{ accepted: boolean; consent_version: string }>("/api/consent", {
      method: "POST",
      body: JSON.stringify({ student_id: studentId, accepted })
    }),
  saveProject: (studentId: string, projectTitle: string, projectGoal: string) =>
    request<{ student_id: string; project_title: string; project_goal: string }>("/api/project", {
      method: "POST",
      body: JSON.stringify({ student_id: studentId, project_title: projectTitle, project_goal: projectGoal })
    }),
  tasks: (studentId: string) =>
    request<{ tasks: PilotTask[] }>(`/api/tasks?student_id=${encodeURIComponent(studentId)}`),
  startSession: (studentId: string, taskId: string) =>
    request<PilotSession>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ student_id: studentId, task_id: taskId })
    }),
  completeSession: (sessionId: string) =>
    request<{ id: string; status: string }>(`/api/sessions/${sessionId}/complete`, {
      method: "POST"
    }),
  saveAnswer: (sessionId: string, answer: string) =>
    request<{ id: string; final_answer: string }>(`/api/sessions/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer })
    }),
  sessionState: (sessionId: string) =>
    request<{
      condition: string;
      status: string;
      final_answer: string | null;
      turns: Turn[];
      worksheet_responses: Array<{ id: string; session_id: string; step_key: string; response: string }>;
    }>(`/api/sessions/${sessionId}/state`),
  sessionSummary: (sessionId: string) =>
    request<{ kind: string; summary: string; final_answer: string | null }>(
      `/api/sessions/${sessionId}/summary`
    ),
  submitFeedback: (studentId: string, rating: number, comment: string) =>
    request<{ id: string; rating: number }>("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ student_id: studentId, rating, comment })
    }),
  submitSus: (studentId: string, answers: number[]) =>
    request<{ id: string; total: number }>("/api/sus", {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        ...Object.fromEntries(answers.map((value, index) => [`q${index + 1}`, value]))
      })
    }),
  dialogueTurn: (sessionId: string, content: string) =>
    request<{ student_turn: Turn; tutor_turn: Turn }>("/api/dialogue/turn", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, content })
    }),
  dialogueHint: (sessionId: string) =>
    request<{ hint: string }>("/api/dialogue/hint", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId })
    }),
  worksheetResponse: (sessionId: string, stepKey: string, prompt: string, response: string) =>
    request<{ id: string }>("/api/worksheet/response", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, step_key: stepKey, prompt, response })
    }),
  adminSummary: (password: string) =>
    request<AdminSummary>("/api/admin/summary", {
      headers: { "X-Admin-Password": password }
    }),
  adminExportJson: (password: string, blinded: boolean) =>
    request<unknown>(`/api/admin/export?format=json&blinded=${blinded}`, {
      headers: { "X-Admin-Password": password }
    }),
  adminExportCsv: async (password: string, blinded: boolean) => {
    const response = await fetch(`${API_BASE}/api/admin/export?format=csv&blinded=${blinded}`, {
      headers: { "X-Admin-Password": password }
    });
    if (!response.ok) throw new Error(response.statusText);
    return response.text();
  }
};
