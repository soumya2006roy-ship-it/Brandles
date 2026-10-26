import { type NextRequest } from "next/server";

const allowedResponseHeaders = ["content-type", "cache-control", "set-cookie", "retry-after", "x-content-type-options", "referrer-policy", "x-frame-options", "cross-origin-opener-policy", "permissions-policy", "content-security-policy", "strict-transport-security"];

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const backend = process.env.BRANDLENS_BACKEND_URL;
  if (!backend) return Response.json({ detail: "The BrandLens API URL is not configured." }, { status: 503 });
  const target = new URL(`/api/v1/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`, backend);
  const headers = new Headers();
  for (const key of ["accept", "content-type", "cookie", "origin", "user-agent", "sec-fetch-site", "x-forwarded-for"]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    for (const name of allowedResponseHeaders) {
      if (name === "set-cookie") {
        for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append(name, cookie);
      } else {
        const value = upstream.headers.get(name);
        if (value) responseHeaders.set(name, value);
      }
    }
    const body = upstream.status === 204 || upstream.status === 304 ? null : await upstream.arrayBuffer();
    return new Response(body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return Response.json({ detail: "The BrandLens service is unavailable." }, { status: 503 });
  }
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
