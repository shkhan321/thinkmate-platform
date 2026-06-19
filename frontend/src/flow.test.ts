import { describe, expect, it } from "vitest";
import {
  canSubmitWorksheet,
  conditionGuide,
  modelModeLabel,
  studentProgress,
  taskActionLabel,
  tourSteps
} from "./flow";

describe("pilot flow helpers", () => {
  it("labels task action by assigned condition", () => {
    expect(taskActionLabel("thinkmate")).toBe("Start discussion");
    expect(taskActionLabel("worksheet")).toBe("Start worksheet");
  });

  it("requires all worksheet steps to have non-empty responses", () => {
    expect(canSubmitWorksheet(["claim", "evidence"], { claim: "A", evidence: "B" })).toBe(true);
    expect(canSubmitWorksheet(["claim", "evidence"], { claim: "A", evidence: " " })).toBe(false);
  });

  it("shows a clear model mode label", () => {
    expect(modelModeLabel("demo")).toContain("Demo");
    expect(modelModeLabel("huggingface")).toContain("Hugging Face");
  });

  it("shows student progress with completed, current, and upcoming steps", () => {
    const progress = studentProgress("tasks");

    expect(progress.map((step) => `${step.label}:${step.status}`)).toEqual([
      "Access code:complete",
      "Consent:complete",
      "Choose task:current",
      "Complete activity:upcoming"
    ]);
  });

  it("keeps the quick tour short and action-oriented", () => {
    const steps = tourSteps();

    expect(steps).toHaveLength(4);
    expect(steps[0].title).toBe("Use your study code");
    expect(steps[3].body).toContain("saved");
  });

  it("explains each condition in student-friendly words", () => {
    expect(conditionGuide("thinkmate")).toContain("chat");
    expect(conditionGuide("worksheet")).toContain("boxes");
  });
});
