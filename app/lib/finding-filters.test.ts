import { describe, expect, it } from "vitest";
import { buildFindingQuery } from "./finding-filters";

describe("buildFindingQuery", () => {
  it("includes only trimmed, non-empty filters", () => {
    const result = new URLSearchParams(buildFindingQuery({ offset: 25, limit: 25, status: " open ", severity: "high", channel: "", search: "  offer mismatch " }));
    expect(Object.fromEntries(result)).toEqual({ offset: "25", limit: "25", status: "open", severity: "high", search: "offer mismatch" });
  });

  it("bounds pagination values", () => {
    const result = new URLSearchParams(buildFindingQuery({ offset: -10, limit: 1000 }));
    expect(result.get("offset")).toBe("0");
    expect(result.get("limit")).toBe("100");
  });
});
