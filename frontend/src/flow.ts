import type { Condition, ModelMode } from "./types";

export type StudentStage = "login" | "consent" | "tasks" | "active" | "complete";
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
  { stage: "login", label: "Access code" },
  { stage: "consent", label: "Consent" },
  { stage: "tasks", label: "Choose task" },
  { stage: "active", label: "Complete activity" }
];

export function taskActionLabel(condition: Condition): string {
  return condition === "thinkmate" ? "Start discussion" : "Start worksheet";
}

export function canSubmitWorksheet(stepKeys: string[], responses: Record<string, string>): boolean {
  return stepKeys.every((key) => (responses[key] || "").trim().length > 0);
}

export function modelModeLabel(mode: ModelMode): string {
  if (mode === "poe") return "Poe model API enabled";
  if (mode === "huggingface") return "Hugging Face model API enabled";
  return "Demo model mode: deterministic Socratic questions";
}

export function studentProgress(stage: StudentStage): ProgressStep[] {
  const currentIndex = stage === "complete" ? progressOrder.length : progressOrder.findIndex((step) => step.stage === stage);

  return progressOrder.map((step, index) => {
    if (index < currentIndex) return { label: step.label, status: "complete" };
    if (index === currentIndex) return { label: step.label, status: "current" };
    return { label: step.label, status: "upcoming" };
  });
}

export function tourSteps(): TourStep[] {
  return [
    {
      title: "Use your study code",
      body: "Enter only the access code given by the research team. Do not type your name or student number."
    },
    {
      title: "Accept consent",
      body: "Read the short notice, then continue only if you agree to take part in the pilot."
    },
    {
      title: "Complete your activity",
      body: "You may be asked to use a ThinkMate chat or a guided worksheet. Follow the task shown on screen."
    },
    {
      title: "Submit and finish",
      body: "Your responses are saved under your study code so the research team can analyse the pilot later."
    }
  ];
}

export function conditionGuide(condition: Condition): string {
  if (condition === "thinkmate") {
    return "You will use a short chat. ThinkMate will ask questions to help you explain your reasoning.";
  }
  return "You will complete guided worksheet boxes. Answer each box in your own words before submitting.";
}
