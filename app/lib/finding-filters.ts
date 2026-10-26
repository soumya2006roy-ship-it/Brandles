export type FindingFilters = {
  offset: number;
  limit: number;
  status?: string;
  severity?: string;
  channel?: string;
  search?: string;
};

export function buildFindingQuery(filters: FindingFilters): string {
  const params = new URLSearchParams({ offset: String(Math.max(0, filters.offset)), limit: String(Math.min(100, Math.max(1, filters.limit))) });
  for (const key of ["status", "severity", "channel", "search"] as const) {
    const value = filters[key]?.trim();
    if (value) params.set(key, value);
  }
  return params.toString();
}
