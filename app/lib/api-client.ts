import type { paths } from "@/app/lib/api-schema";

export type OrganizationRole = "admin" | "creator" | "reviewer";
export type OrganizationStatus = "draft" | "pending_verification" | "approved" | "rejected" | "more_information_required";
export type User = paths["/api/v1/auth/me"]["get"]["responses"]["200"]["content"]["application/json"];
export type Organization = Omit<paths["/api/v1/orgs/{organization_id}"]["get"]["responses"]["200"]["content"]["application/json"], "verification_status"> & { verification_status: OrganizationStatus };
export type OrganizationSummary = paths["/api/v1/orgs"]["get"]["responses"]["200"]["content"]["application/json"][number];
export type Invite = paths["/api/v1/orgs/{organization_id}/invites"]["get"]["responses"]["200"]["content"]["application/json"][number];
export type VerificationHistory = paths["/api/v1/platform/verifications/{organization_id}/history"]["get"]["responses"]["200"]["content"]["application/json"][number];
export type RegisterInput = paths["/api/v1/auth/register"]["post"]["requestBody"]["content"]["application/json"];
export type LoginInput = paths["/api/v1/auth/login"]["post"]["requestBody"]["content"]["application/json"];
export type CreateOrganizationInput = paths["/api/v1/orgs"]["post"]["requestBody"]["content"]["application/json"];
export type CreateInviteInput = paths["/api/v1/orgs/{organization_id}/invites"]["post"]["requestBody"]["content"]["application/json"];

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

function getErrorMessage(value: unknown): string | undefined {
  if (typeof value === "string") return value.trim() || undefined;
  if (Array.isArray(value)) {
    const messages = value.map((item) => {
      if (!item || typeof item !== "object") return getErrorMessage(item);
      const entry = item as { loc?: unknown; msg?: unknown; message?: unknown };
      const message = getErrorMessage(entry.msg) ?? getErrorMessage(entry.message);
      if (!message) return getErrorMessage(item);
      const location = Array.isArray(entry.loc)
        ? entry.loc.filter((part) => !["body", "query", "path"].includes(String(part))).map(String).join(".")
        : "";
      return location ? `${location}: ${message}` : message;
    }).filter((message): message is string => Boolean(message));
    return messages.length ? messages.join("; ") : undefined;
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return getErrorMessage(record.detail) ?? getErrorMessage(record.message) ?? getErrorMessage(record.msg) ?? getErrorMessage(record.error);
  }
  return undefined;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const response = await fetch(`/api/product/${path.replace(/^\//, "")}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: { ...(init.body && !isFormData ? { "content-type": "application/json" } : {}), ...init.headers },
  });
  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body: unknown = await response.json();
      const detail = body && typeof body === "object" && "detail" in body
        ? (body as { detail?: unknown }).detail
        : body;
      message = getErrorMessage(detail) ?? message;
    } catch { /* Keep the accessible generic error if the response is not JSON. */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
