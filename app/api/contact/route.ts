import { NextResponse } from "next/server";
import { Resend } from "resend";
import { z } from "zod";

const plainText = (value: string) => value
  .replace(/<[^>]*>/g, "")
  .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
  .trim();

const contactSchema = z.object({
  name: z.string().transform(plainText).pipe(z.string().min(2, "Enter your name.").max(100, "Keep your name under 100 characters.")),
  email: z.string().trim().email("Enter a valid email address.").max(254, "That email address is too long.").transform((value) => value.toLowerCase()),
  organization: z.string().optional().default("").transform(plainText).pipe(z.string().max(120, "Keep this under 120 characters.")),
  message: z.string().transform(plainText).pipe(z.string().min(20, "Add a little more detail (at least 20 characters).").max(3000, "Keep your message under 3,000 characters.")),
  website: z.string().max(300).optional().default(""),
});

type RateEntry = { startedAt: number; count: number };
const rateWindowMs = 60 * 60 * 1000;
const maxSubmissions = 5;
const rateEntries = new Map<string, RateEntry>();

function isRateLimited(key: string, now = Date.now()) {
  for (const [storedKey, entry] of rateEntries) {
    if (now - entry.startedAt >= rateWindowMs) rateEntries.delete(storedKey);
  }
  const current = rateEntries.get(key);
  if (!current || now - current.startedAt >= rateWindowMs) {
    rateEntries.set(key, { startedAt: now, count: 1 });
    return false;
  }
  if (current.count >= maxSubmissions) return true;
  current.count += 1;
  return false;
}

export async function POST(request: Request) {
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > 12_000) return NextResponse.json({ message: "Your message is too large. Please shorten it and try again." }, { status: 413 });

  let raw: unknown;
  try {
    const reader = request.body?.getReader();
    if (!reader) return NextResponse.json({ message: "We couldn’t read that submission. Please try again." }, { status: 400 });
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 12_000) {
        await reader.cancel();
        return NextResponse.json({ message: "Your message is too large. Please shorten it and try again." }, { status: 413 });
      }
      chunks.push(value);
    }
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.byteLength;
    }
    raw = JSON.parse(new TextDecoder().decode(body));
  } catch {
    return NextResponse.json({ message: "We couldn’t read that submission. Please try again." }, { status: 400 });
  }

  const parsed = contactSchema.safeParse(raw);
  if (!parsed.success) {
    const fields = parsed.error.issues.reduce<Record<string, string>>((result, issue) => {
      const key = String(issue.path[0] ?? "form");
      if (!result[key]) result[key] = issue.message.trim();
      return result;
    }, {});
    return NextResponse.json({ message: "Check the highlighted fields and try again.", fields }, { status: 400 });
  }

  // Honeypot submissions look successful to bots but are not stored or emailed.
  if (parsed.data.website) return NextResponse.json({ message: "Thanks : your note has been received." });

  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const remoteAddress = request.headers.get("x-real-ip")?.trim() || forwarded || "unknown";
  if (isRateLimited(remoteAddress)) {
    return NextResponse.json({ message: "Please wait a while before sending another message." }, { status: 429 });
  }

  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.CONTACT_FROM_EMAIL;
  const to = process.env.CONTACT_TO_EMAIL;
  const replyTo = process.env.CONTACT_REPLY_TO;
  if (!apiKey || !from || !to) {
    return NextResponse.json({ message: "The contact form is not configured yet. Please try again later." }, { status: 503 });
  }

  const resend = new Resend(apiKey);
  const { name, email, organization, message } = parsed.data;
  try {
    const results = await Promise.all([
      resend.emails.send({
        from,
        to,
        replyTo: email,
        subject: `BrandLens contact from ${name}`,
        text: `Name: ${name}\nEmail: ${email}\nOrganization: ${organization || "Not provided"}\n\nMessage:\n${message}`,
      }),
      resend.emails.send({
        from,
        to: email,
        ...(replyTo ? { replyTo } : {}),
        subject: "We received your BrandLens message",
        text: `Hi ${name},\n\nThanks for contacting BrandLens. We received your message and will review it.\n\nYour message:\n${message}\n\nBrandLens\nOne brand. Every channel. One voice you can trust.`,
      }),
    ]);
    if (results.some((result) => result.error)) {
      console.error("Contact email delivery failed", results.map((result) => result.error?.name ?? null));
      return NextResponse.json({ message: "We couldn’t deliver your message just now. Please try again later." }, { status: 502 });
    }
    return NextResponse.json({ message: "Thanks : your message is on its way. We’ve sent a confirmation to your email." });
  } catch (error) {
    console.error("Contact email delivery failed", error instanceof Error ? error.name : "unknown error");
    return NextResponse.json({ message: "We couldn’t deliver your message just now. Please try again later." }, { status: 502 });
  }
}
