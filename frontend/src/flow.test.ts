import { describe, expect, it } from "vitest";
import { canSubmitWorksheet, modelModeLabel, taskActionLabel } from "./flow";

describe("pilot flow helpers", () => {
  it("labels task action by assigned condition", () => {
    expect(taskActionLabel("thinkmate")).toBe("Start ThinkMate");
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
});
