import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { ProductShell } from "@/app/app/product-shell";

export default async function ProductLayout({ children }: Readonly<{ children: ReactNode }>) {
  const backend = process.env.BRANDLENS_BACKEND_URL;
  const cookieName = process.env.SESSION_COOKIE_NAME ?? "brandlens_session";
  const session = (await cookies()).get(cookieName)?.value;
  if (!backend || !session) redirect("/login");

  let response: Response;
  try {
    response = await fetch(new URL("/api/v1/auth/me", backend), {
      headers: { cookie: `${cookieName}=${encodeURIComponent(session)}` },
      cache: "no-store",
    });
  } catch {
    return <main className="page-shell"><p role="alert">The BrandLens API is unavailable. Try again when the service is ready.</p></main>;
  }
  if (response.status === 401) redirect("/login");
  if (!response.ok) return <main className="page-shell"><p role="alert">The BrandLens API could not verify your session. Try again shortly.</p></main>;
  return <ProductShell>{children}</ProductShell>;
}
