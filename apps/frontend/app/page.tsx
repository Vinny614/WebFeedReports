import { api, Source, SourceHealth } from "@/lib/api";

function formatDate(value?: string | null): string {
  if (!value) return "Never";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

const STATUS_LABELS: Record<SourceHealth["status"], string> = {
  never: "Not yet run",
  healthy: "Healthy",
  degraded: "Needs attention",
  failed: "Failed",
};

export default async function DashboardPage() {
  let sources: Source[] = [];
  let health: SourceHealth[] = [];
  let error: string | null = null;
  try {
    [sources, health] = await Promise.all([
      api.listSources(),
      api.listSourceHealth(),
    ]);
  } catch (e) {
    error = (e as Error).message;
  }

  return (
    <div>
      <h1 className="govuk-heading-xl">Dashboard</h1>
      <p className="govuk-body">
        Current ingestion coverage and source quality. A source can need
        attention even when its page was reachable but returned no useful content.
      </p>

      {error && (
        <div className="govuk-error-summary" role="alert" aria-labelledby="error-summary-title">
          <h2 className="govuk-error-summary__title" id="error-summary-title">
            There is a problem
          </h2>
          <p className="govuk-body govuk-!-margin-bottom-0">
            Could not load sources (is the API running?): {error}
          </p>
        </div>
      )}

      {!error && sources.length === 0 && (
        <p className="govuk-inset-text">No enabled sources are configured.</p>
      )}

      <div className="app-health-grid">
        {sources.map((source) => {
          const current = health.find((item) => item.source_id === source.id) ?? {
            source_id: source.id,
            status: "never" as const,
            success_count: 0,
            failure_count: 0,
            consecutive_failures: 0,
            document_count: 0,
            indexed_document_count: 0,
            chunk_count: 0,
            warnings: [],
          };
          return (
            <article className={`app-health-card app-health-card--${current.status}`} key={source.id}>
              <div className="app-health-card__header">
                <h2 className="govuk-heading-m">{source.id}</h2>
                <strong className={`app-health-tag app-health-tag--${current.status}`}>
                  {STATUS_LABELS[current.status]}
                </strong>
              </div>
              <dl className="app-health-list">
                <div><dt>Last attempt</dt><dd>{formatDate(current.last_attempt_at)}</dd></div>
                <div><dt>Last success</dt><dd>{formatDate(current.last_success_at)}</dd></div>
                <div><dt>Newest item</dt><dd>{formatDate(current.newest_published_at)}</dd></div>
                <div><dt>Documents indexed</dt><dd>{current.indexed_document_count} of {current.document_count}</dd></div>
                <div><dt>Chunks</dt><dd>{current.chunk_count}</dd></div>
              </dl>
              {(current.warnings.length > 0 || current.latest_error) && (
                <p className="govuk-body-s app-health-card__message">
                  {current.latest_error ?? current.warnings.join(", ").split("_").join(" ")}
                </p>
              )}
              <p className="govuk-body-s">
                <a className="govuk-link" href={source.url} target="_blank" rel="noreferrer">
                  Open source
                </a>{" · "}{source.type}{" · "}{source.tags.join(", ")}
              </p>
            </article>
          );
        })}
      </div>
    </div>
  );
}
