import type { Condition, ModelMode } from "./types";

export type StudentStage =
  | "login"
  | "consent"
  | "project"
  | "tasks"
  | "active"
  | "wrapup"
  | "complete"
  | "review";
export type ProgressStatus = "complete" | "current" | "upcoming";

export interface ProgressStep {
  label: string;
  status: ProgressStatus;
}

export interface TourStep {
  title: string;
  body: string;
}

const progressOrder: Array<{ stage: StudentStage; label: string }> = [
  { stage: "login", label: "Sign in" },
  { stage: "consent", label: "Agree" },
  { stage: "project", label: "Your project" },
  { stage: "tasks", label: "Choose activity" },
  { stage: "active", label: "Think it through" }
];

export const COURSES: Array<{ value: string; label: string; code: string; blurb: string }> = [
  {
    value: "engineering",
    label: "Engineering",
    code: "AERO / MECH 590",
    blurb: "Any Mech or Aero capstone project"
  },
  {
    value: "psychology",
    label: "Psychology",
    code: "PSYC 485",
    blurb: "Any Psychology capstone project"
  }
];

// The five reasoning moves ThinkMate walks a student through. Drives the live
// "reasoning map" — the simple visual that shows how the thinking is building.
export interface ReasoningStep {
  key: string;
  label: string;
  moveType: string;
  hint: string;
}

export const REASONING_STEPS: ReasoningStep[] = [
  { key: "clarify", label: "Clarify", moveType: "clarification", hint: "Make your claim clear" },
  { key: "evidence", label: "Evidence", moveType: "evidence_probe", hint: "Back it with reasons" },
  { key: "assumption", label: "Assumptions", moveType: "assumption_probe", hint: "Spot what you take for granted" },
  { key: "counterview", label: "Counter-view", moveType: "counterview", hint: "Face a strong objection" },
  { key: "reflection", label: "Reflect", moveType: "reflection", hint: "Keep or change your view" }
];

export function coveredReasoning(moveTypes: Array<string | null | undefined>): Set<string> {
  const seen = new Set(moveTypes.filter(Boolean) as string[]);
  return new Set(REASONING_STEPS.filter((step) => seen.has(step.moveType)).map((step) => step.key));
}

export function courseLabel(course: string): string {
  return COURSES.find((item) => item.value === course)?.label ?? formatTitle(course);
}

export function courseCode(course: string): string {
  return COURSES.find((item) => item.value === course)?.code ?? "";
}

export function projectDraftKey(studentId: string | null | undefined): string | null {
  return studentId ? `thinkmate.projectdraft.${studentId}` : null;
}

export function projectExamples(course: string): { title: string; goal: string } {
  if (course === "psychology") {
    return {
      title: "e.g. Does sleep quality affect students' exam scores?",
      goal: "e.g. Decide whether to use a survey or a lab experiment"
    };
  }
  return {
    title: "e.g. A drone arm that folds for storage",
    goal: "e.g. Decide which hinge design is strong but still light"
  };
}

function formatTitle(value: string): string {
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function firstName(name: string | null | undefined): string {
  if (!name) return "there";
  return name.trim().split(/\s+/)[0] || "there";
}

export function taskActionLabel(condition: Condition): string {
  return condition === "thinkmate" ? "Start discussion" : "Start worksheet";
}

export function conditionTitle(condition: Condition): string {
  return condition === "thinkmate" ? "ThinkMate discussion" : "Guided worksheet";
}

export function canSubmitWorksheet(stepKeys: string[], responses: Record<string, string>): boolean {
  return stepKeys.every((key) => (responses[key] || "").trim().length > 0);
}

export function modelModeLabel(mode: ModelMode): string {
  if (mode === "poe") return "AI tutor online";
  if (mode === "huggingface") return "AI tutor online";
  return "Demo mode";
}

export function studentProgress(stage: StudentStage): ProgressStep[] {
  const currentIndex =
    stage === "complete" ? progressOrder.length : progressOrder.findIndex((step) => step.stage === stage);

  return progressOrder.map((step, index) => {
    if (index < currentIndex) return { label: step.label, status: "complete" };
    if (index === currentIndex) return { label: step.label, status: "current" };
    return { label: step.label, status: "upcoming" };
  });
}

export function tourSteps(): TourStep[] {
  return [
    {
      title: "Sign in with your name",
      body: "Just type your name and pick your course. No password, and your work is saved automatically."
    },
    {
      title: "Agree to take part",
      body: "Read the short notice and continue only if you are happy to join this learning activity."
    },
    {
      title: "Think it through",
      body: "You will either chat with ThinkMate or fill in a guided worksheet. Answer in your own words."
    },
    {
      title: "Submit and you're done",
      body: "Your responses are saved so your reasoning can be reviewed later. You can come back any time."
    }
  ];
}

export function conditionGuide(condition: Condition): string {
  if (condition === "thinkmate") {
    return "You will use a short chat. ThinkMate will ask questions to help you explain your reasoning.";
  }
  return "You will complete guided worksheet boxes. Answer each box in your own words before submitting.";
}
