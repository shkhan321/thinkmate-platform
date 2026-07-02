import { describe, expect, it } from "vitest";
import {
  SUS_ITEMS,
  buildReasoningTree,
  buildWorksheetTree,
  canSubmitWorksheet,
  conditionGuide,
  courseLabel,
  coveredReasoning,
  firstName,
  isLowEffortAnswer,
  modelModeLabel,
  studentProgress,
  susTotal,
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

  it("never lets a stuck reply fill or overwrite a tree node", () => {
    const tree = buildReasoningTree([
      turn("student", "I will use carbon fibre for the arm because it is light and stiff"),
      turn("tutor", "What exactly is your claim?", "clarification"),
      turn("student", "idk"),
      turn("tutor", "What exactly is your claim?", "clarification"),
      turn("student", "not sure")
    ]);
    const byKey = Object.fromEntries(tree.map((node) => [node.key, node]));
    // The real claim survives; the low-effort replies neither overwrite nor fill it.
    expect(byKey.claim.full).toContain("carbon fibre");
    expect(byKey.claim.full).not.toContain("idk");
    expect(byKey.claim.full).not.toContain("not sure");
    // Nothing downstream is marked done by the junk replies.
    expect(tree.filter((node) => node.filled).map((node) => node.key)).toEqual(["claim"]);
    // The "now" highlight points at the next real gap, not a finished node.
    expect(tree.find((node) => node.current)?.key).toBe("evidence");
  });

  it("keeps the original claim even when a later clarification answer is substantive", () => {
    const tree = buildReasoningTree([
      turn("student", "Carbon fibre is the best hinge material"),
      turn("tutor", "What exactly is your claim?", "clarification"),
      turn("student", "I mean carbon fibre composite rather than aluminium")
    ]);
    expect(tree.find((node) => node.key === "claim")?.full).toBe("Carbon fibre is the best hinge material");
  });

  it("ignores an answer that follows a tutor turn with an unknown move (no misroute to claim)", () => {
    const tree = buildReasoningTree([
      turn("student", "Carbon fibre claim"),
      turn("tutor", "Some odd question", "weird_unknown_move"),
      turn("student", "this should not become the claim")
    ]);
    expect(tree.find((node) => node.key === "claim")?.full).toBe("Carbon fibre claim");
    expect(tree.filter((node) => node.filled).map((node) => node.key)).toEqual(["claim"]);
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

  it("recognises Arabic stuck and give-up phrases as low effort (backend lockstep)", () => {
    expect(isLowEffortAnswer("لا أعرف")).toBe(true);
    expect(isLowEffortAnswer("ساعدني")).toBe(true);
    expect(isLowEffortAnswer("أعطني الجواب")).toBe(true);
    // A substantive Arabic answer must not be flagged as stuck.
    expect(isLowEffortAnswer("لقد اخترت المفصل الفولاذي لأن التحميل الدوري يسبب الكلال في المفصل المرن")).toBe(false);
  });

  it("scores the SUS with the standard 0-100 formula (backend lockstep)", () => {
    expect(SUS_ITEMS).toHaveLength(10);
    // Best possible: odd items 5, even items 1.
    expect(susTotal([5, 1, 5, 1, 5, 1, 5, 1, 5, 1])).toBe(100);
    // All neutral 3s land exactly in the middle.
    expect(susTotal([3, 3, 3, 3, 3, 3, 3, 3, 3, 3])).toBe(50);
    // Worst possible: odd items 1, even items 5.
    expect(susTotal([1, 5, 1, 5, 1, 5, 1, 5, 1, 5])).toBe(0);
  });
});
