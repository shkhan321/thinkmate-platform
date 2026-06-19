import { describe, expect, test } from "vitest";
import { resolveApiBase } from "./api";

describe("resolveApiBase", () => {
  test("uses same-origin API paths when no API URL is configured", () => {
    expect(resolveApiBase()).toBe("");
  });

  test("uses configured API URL without a trailing slash", () => {
    expect(resolveApiBase("https://thinkmate.example.com/")).toBe("https://thinkmate.example.com");
  });
});
