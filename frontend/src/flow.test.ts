import { describe, expect, it } from "vitest";
import {
  buildReasoningTree,
  buildWorksheetTree,
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
import type { Turn } from "./types";

function turn(role: "student" | "tutor", content: string, moveType?: string): Turn {
  return { id: "x", session_id: "s", turn_number: 0, role, content, move_type: moveType ?? null, safeguard_flag: false };
}

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
    expect(modelModeLabel("gemini")).toContain("online");
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

  it("builds a bottom-up reasoning tree from the student's own chat answers", () => {
    const tree = buildReasoningTree([
      turn("student", "I will use a nylon hinge because it resists fatigue"),
      turn("tutor", "What evidence supports that?", "evidence_probe"),
      turn("student", "Fatigue tests on similar parts passed"),
      turn("tutor", "What assumption are you making?", "assumption_probe")
    ]);

    // Order is bottom-up: claim is the foundation, revise is the top.
    expect(tree.map((node) => node.key)).toEqual(["claim", "evidence", "assumption", "counterview", "revise"]);
    const byKey = Object.fromEntries(tree.map((node) => [node.key, node]));
    // The opening message is the claim; the next answers the evidence question.
    expect(byKey.claim.filled).toBe(true);
    expect(byKey.claim.full).toContain("nylon hinge");
    expect(byKey.evidence.filled).toBe(true);
    expect(byKey.evidence.full).toContain("Fatigue tests");
    // The tutor just asked about assumptions and the student hasn't answered yet.
    expect(byKey.assumption.filled).toBe(false);
    expect(byKey.assumption.current).toBe(true);
    expect(byKey.revise.filled).toBe(false);
    // Each node holds the student's own words only (no tutor text leaks in).
    expect(tree.some((node) => node.full.includes("What evidence"))).toBe(false);
  });

  it("builds the same tree shape from the worksheet's saved answers", () => {
    const tree = buildWorksheetTree([
      { step_key: "claim", response: "A diary study fits best" },
      { step_key: "reflection", response: "I would keep the diary method" }
    ]);
    const byKey = Object.fromEntries(tree.map((node) => [node.key, node]));
    expect(byKey.claim.filled).toBe(true);
    expect(byKey.revise.filled).toBe(true);
    expect(byKey.evidence.filled).toBe(false);
  });
});
