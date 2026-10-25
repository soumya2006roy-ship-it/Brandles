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

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/product/${path.replace(/^\//, "")}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: { ...(init.body ? { "content-type": "application/json" } : {}), ...init.headers },
  });
  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) message = body.detail;
    } catch { /* Keep the accessible generic error if the response is not JSON. */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
