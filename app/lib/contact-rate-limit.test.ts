import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { consumeContactSubmission, resetLocalContactRateLimitForTests } from "./contact-rate-limit";

describe("contact rate limiter", () => {
  beforeEach(() => {
    vi.stubEnv("REDIS_URL", "");
    vi.stubEnv("NODE_ENV", "test");
  });
  afterEach(() => resetLocalContactRateLimitForTests());
  afterEach(() => vi.unstubAllEnvs());

  it("allows five submissions and provides a retry delay on the sixth", async () => {
    const start = 1_800_000_000_000;
    const firstFive = await Promise.all(Array.from({ length: 5 }, () => consumeContactSubmission("203.0.113.12", start)));
    expect(firstFive.every((result) => !result.limited)).toBe(true);

    const blocked = await consumeContactSubmission("203.0.113.12", start + 1_000);
    expect(blocked.limited).toBe(true);
    expect(blocked.retryAfter).toBe(3599);
  });

  it("uses the same bucket when no trusted client IP is provided", async () => {
    const start = 1_800_000_000_000;
    for (let index = 0; index < 5; index += 1) await consumeContactSubmission(null, start);
    expect((await consumeContactSubmission(null, start)).limited).toBe(true);
  });

  it("enforces the quota across concurrent local calls", async () => {
    const results = await Promise.all(Array.from({ length: 20 }, () => consumeContactSubmission("198.51.100.42")));
    expect(results.filter((result) => !result.limited)).toHaveLength(5);
    expect(results.filter((result) => result.limited)).toHaveLength(15);
  });
});
