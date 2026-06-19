import type { Condition, ModelMode } from "./types";

export function taskActionLabel(condition: Condition): string {
  return condition === "thinkmate" ? "Start ThinkMate" : "Start worksheet";
}

export function canSubmitWorksheet(stepKeys: string[], responses: Record<string, string>): boolean {
  return stepKeys.every((key) => (responses[key] || "").trim().length > 0);
}

export function modelModeLabel(mode: ModelMode): string {
  return mode === "huggingface"
    ? "Hugging Face model API enabled"
    : "Demo model mode: deterministic Socratic questions";
}
