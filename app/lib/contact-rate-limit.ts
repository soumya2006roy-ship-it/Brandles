import { createHash } from "node:crypto";
import { isIP } from "node:net";
import { createClient } from "redis";

const windowSeconds = 60 * 60;
const maxSubmissions = 5;
const localEntries = new Map<string, { startedAt: number; count: number }>();
const redisScript = `
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return { count, redis.call('TTL', KEYS[1]) }
`;

type ContactRedis = ReturnType<typeof createClient>;
type ContactGlobal = typeof globalThis & { __brandlensContactRedis?: ContactRedis; __brandlensContactRedisConnect?: Promise<ContactRedis> };

function getRedisClient(): ContactRedis | null {
  const url = process.env.REDIS_URL;
  if (!url) return null;
  const shared = globalThis as ContactGlobal;
  if (!shared.__brandlensContactRedis) {
    shared.__brandlensContactRedis = createClient({ url });
    // Keep connection errors handled; callers fail closed in production.
    shared.__brandlensContactRedis.on("error", () => undefined);
  }
  return shared.__brandlensContactRedis;
}

function localRateLimit(ip: string, now: number): { limited: boolean; retryAfter: number } {
  for (const [key, entry] of localEntries) {
    if (now - entry.startedAt >= windowSeconds * 1000) localEntries.delete(key);
  }
  const current = localEntries.get(ip);
  if (!current || now - current.startedAt >= windowSeconds * 1000) {
    if (localEntries.size >= 10_000) localEntries.delete(localEntries.keys().next().value ?? ip);
    localEntries.set(ip, { startedAt: now, count: 1 });
    return { limited: false, retryAfter: windowSeconds };
  }
  if (current.count >= maxSubmissions) {
    return { limited: true, retryAfter: Math.max(1, Math.ceil((current.startedAt + windowSeconds * 1000 - now) / 1000)) };
  }
  current.count += 1;
  return { limited: false, retryAfter: Math.max(1, Math.ceil((current.startedAt + windowSeconds * 1000 - now) / 1000)) };
}

export async function consumeContactSubmission(clientIpHeader: string | null, now = Date.now()): Promise<{ limited: boolean; retryAfter: number; unavailable?: boolean }> {
  // `X-Real-IP` is accepted only from an ingress configured to overwrite it.
  // Do not use X-Forwarded-For directly because a client can forge that header.
  const candidate = clientIpHeader?.trim() ?? "";
  if (!isIP(candidate) && process.env.NODE_ENV === "production") {
    return { limited: false, retryAfter: windowSeconds, unavailable: true };
  }
  const ip = isIP(candidate) ? candidate : "unknown";
  const client = getRedisClient();
  if (client) {
    try {
      const shared = globalThis as ContactGlobal;
      if (!client.isOpen) {
        shared.__brandlensContactRedisConnect ??= client.connect().then(() => client).catch((error: unknown) => {
          shared.__brandlensContactRedisConnect = undefined;
          throw error;
        });
        await shared.__brandlensContactRedisConnect;
      }
      const digest = createHash("sha256").update(ip).digest("hex");
      const [count, ttl] = await client.eval(redisScript, { keys: [`brandlens:contact:${digest}`], arguments: [String(windowSeconds)] }) as [number, number];
      return { limited: count > maxSubmissions, retryAfter: Math.max(1, ttl) };
    } catch {
      if (process.env.NODE_ENV === "production") return { limited: false, retryAfter: windowSeconds, unavailable: true };
    }
  } else if (process.env.NODE_ENV === "production") {
    return { limited: false, retryAfter: windowSeconds, unavailable: true };
  }
  return localRateLimit(ip, now);
}

export function resetLocalContactRateLimitForTests() {
  localEntries.clear();
}
