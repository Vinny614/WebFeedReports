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
  published_at?: string | null;
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

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface JobStatusResponse {
  job_id: string;
  type: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  error?: string | null;
  result_ref?: string | null;
}

export interface ReportItem {
  title: string;
  url?: string | null;
  source?: string | null;
  published_at?: string | null;
  summary: string;
}

export interface ReportSection {
  heading: string;
  style: "narrative" | "items";
  content: string;
  items: ReportItem[];
}

export interface ReportTemplateSection {
  heading: string;
  style: "narrative" | "items";
  guidance?: string | null;
  query?: string | null;
  tags: string[];
}

export interface ReportTemplate {
  id: string;
  name: string;
  description?: string | null;
  default_query?: string | null;
  sections: ReportTemplateSection[];
}

export interface RecentHeadingSet {
  name?: string | null;
  sections: ReportTemplateSection[];
  used_at: string;
}

export interface ReportCitation {
  source_id: string;
  title?: string | null;
  url?: string | null;
}

export interface BriefingReport {
  report_id: string;
  title: string;
  query: string;
  generated_at: string;
  summary: string;
  sections: ReportSection[];
  citations: ReportCitation[];
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
  query: (
    query: string,
    opts: {
      top?: number;
      sourceIds?: string[];
      topics?: string[];
      dateFrom?: string | null;
      dateTo?: string | null;
    } = {}
  ) =>
    http<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({
        query,
        top: opts.top ?? 10,
        source_ids: opts.sourceIds ?? [],
        tags: opts.topics ?? [],
        date_from: opts.dateFrom ?? null,
        date_to: opts.dateTo ?? null,
      }),
    }),
  submitReport: (payload: {
    query: string;
    title?: string;
    tags?: string[];
    source_ids?: string[];
    date_from?: string | null;
    date_to?: string | null;
    template_id?: string | null;
    sections?: ReportTemplateSection[] | null;
  }) =>
    http<JobSubmitted>("/reports", {
      method: "POST",
      body: JSON.stringify({
        query: payload.query,
        title: payload.title,
        tags: payload.tags ?? [],
        source_ids: payload.source_ids ?? [],
        date_from: payload.date_from ?? null,
        date_to: payload.date_to ?? null,
        template_id: payload.template_id ?? null,
        sections: payload.sections ?? null,
      }),
    }),
  listReportTemplates: () => http<ReportTemplate[]>("/reports/templates"),
  listRecentHeadings: () =>
    http<RecentHeadingSet[]>("/reports/recent-headings"),
  getReportJob: (jobId: string) =>
    http<JobStatusResponse>(`/jobs/report/${jobId}`),
  getReport: (reportId: string) =>
    http<BriefingReport>(`/reports/${reportId}`),
};
