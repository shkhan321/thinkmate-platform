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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
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
  start: (name: string, course: string) =>
    request<Student>("/api/auth/start", {
      method: "POST",
      body: JSON.stringify({ name, course })
    }),
  accessCode: (accessCode: string) =>
    request<Student>("/api/auth/access-code", {
      method: "POST",
      body: JSON.stringify({ access_code: accessCode })
    }),
  consent: (studentId: string) =>
    request<{ accepted: boolean; consent_version: string }>("/api/consent", {
      method: "POST",
      body: JSON.stringify({ student_id: studentId, accepted: true })
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
  sessionSummary: (sessionId: string) =>
    request<{ kind: string; summary: string }>(`/api/sessions/${sessionId}/summary`),
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
