export type Condition = "thinkmate" | "worksheet";
export type ModelMode = "demo" | "huggingface" | "poe";

export interface Health {
  status: string;
  app_env: string;
  database: string;
  model_mode: ModelMode;
  model_name?: string;
  hf_model: string;
  consent_version: string;
}

export interface Student {
  student_id: string;
  access_code: string;
  course: string;
  sequence: "A" | "B";
  consent_accepted: boolean;
}

export interface WorksheetStep {
  key: string;
  label: string;
  prompt: string;
}

export interface PilotTask {
  id: string;
  course: string;
  task_number: number;
  title: string;
  scenario: string;
  worksheet_steps: WorksheetStep[];
  condition: Condition;
}

export interface PilotSession {
  id: string;
  student_id: string;
  task_id: string;
  condition: Condition;
  status: string;
}

export interface Turn {
  id: string;
  session_id: string;
  turn_number: number;
  role: "student" | "tutor";
  content: string;
  move_type?: string | null;
  paul_elder_target?: string | null;
  bloom_level?: string | null;
  safeguard_flag: boolean;
}

export interface AdminSummary {
  students: number;
  sessions: number;
  turns: number;
  worksheet_responses: number;
}
