import { describe, expect, it } from "vitest";
import {
  canSubmitWorksheet,
  conditionGuide,
  courseLabel,
  coveredReasoning,
  firstName,
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

  it("shows a friendly model mode label", () => {
    expect(modelModeLabel("poe")).toContain("online");
    expect(modelModeLabel("demo")).toContain("Demo");
  });

  it("shows student progress with completed, current, and upcoming steps", () => {
    const progress = studentProgress("tasks");

    expect(progress.map((step) => `${step.label}:${step.status}`)).toEqual([
      "Sign in:complete",
      "Agree:complete",
      "Your project:complete",
      "Choose activity:current",
      "Think it through:upcoming"
    ]);
  });

  it("keeps the quick tour short and action-oriented", () => {
    const steps = tourSteps();

    expect(steps).toHaveLength(4);
    expect(steps[0].title).toBe("Sign in with your name");
    expect(steps[3].body).toContain("saved");
  });

  it("explains each condition in student-friendly words", () => {
    expect(conditionGuide("thinkmate")).toContain("chat");
    expect(conditionGuide("worksheet")).toContain("boxes");
  });

  it("derives a friendly first name with a safe fallback", () => {
    expect(firstName("Aisha Khalifa")).toBe("Aisha");
    expect(firstName("   ")).toBe("there");
    expect(firstName(null)).toBe("there");
  });

  it("maps course values to readable labels", () => {
    expect(courseLabel("engineering")).toBe("Engineering");
    expect(courseLabel("psychology")).toBe("Psychology");
  });

  it("tracks which reasoning steps the dialogue has covered", () => {
    const covered = coveredReasoning(["clarification", "evidence_probe", null]);
    expect(covered.has("clarify")).toBe(true);
    expect(covered.has("evidence")).toBe(true);
    expect(covered.has("assumption")).toBe(false);
  });
});
