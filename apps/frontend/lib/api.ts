// Typed API client for the WebFeedReports API service.
// The frontend talks only to the API; the API holds all Azure access via
// Managed Identity. No secrets or Azure credentials live in the frontend.

function baseUrl(): string {
  // Server (SSR / route handlers): call the API directly via the runtime env
  // var injected by the Container App. Browser: call same-origin and let the
  // Next server proxy forward to the API, so no API URL is baked into the
  // client bundle and the API can stay internal-only.
  if (typeof window === "undefined") {
    return process.env.API_BASE_URL ?? "http://localhost:8000";
  }
  return "/api";
}

export interface QueryResultItem {
  chunk_id: string;
  document_id: string;
  source_id: string;
  score: number;
  title?: string | null;
  url?: string | null;
  snippet: string;
}

export interface QueryResponse {
  query: string;
  items: QueryResultItem[];
}

export interface JobSubmitted {
  job_id: string;
  type: string;
  status: string;
}

export interface Source {
  id: string;
  type: string;
  url: string;
  enabled: boolean;
  tags: string[];
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  listSources: () => http<Source[]>("/sources"),
  refreshSources: (sourceIds?: string[]) =>
    http<JobSubmitted>("/sources/refresh", {
      method: "POST",
      body: JSON.stringify(sourceIds ?? null),
    }),
  query: (query: string, top = 10, tags: string[] = []) =>
    http<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({ query, top, tags }),
    }),
  submitReport: (query: string, title?: string, tags: string[] = []) =>
    http<JobSubmitted>("/reports", {
      method: "POST",
      body: JSON.stringify({ query, title, tags }),
    }),
};
