import type { Condition, ModelMode } from "./types";

export function taskActionLabel(condition: Condition): string {
  return condition === "thinkmate" ? "Start ThinkMate" : "Start worksheet";
}

export function canSubmitWorksheet(stepKeys: string[], responses: Record<string, string>): boolean {
  return stepKeys.every((key) => (responses[key] || "").trim().length > 0);
}

export function modelModeLabel(mode: ModelMode): string {
  if (mode === "poe") return "Poe model API enabled";
  if (mode === "huggingface") return "Hugging Face model API enabled";
  return "Demo model mode: deterministic Socratic questions";
}
