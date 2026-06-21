import { api, Source } from "@/lib/api";

export default async function DashboardPage() {
  let sources: Source[] = [];
  let error: string | null = null;
  try {
    sources = await api.listSources();
  } catch (e) {
    error = (e as Error).message;
  }

  return (
    <div>
      <h1 className="govuk-heading-xl">Dashboard</h1>
      <p className="govuk-body">
        Configured ingestion sources. Use Search to explore indexed content and
        Reports to generate a briefing.
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

      <table className="govuk-table">
        <caption className="govuk-table__caption">Ingestion sources</caption>
        <thead>
          <tr>
            <th scope="col" className="govuk-table__header">ID</th>
            <th scope="col" className="govuk-table__header">Type</th>
            <th scope="col" className="govuk-table__header">URL</th>
            <th scope="col" className="govuk-table__header">Tags</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => (
            <tr key={s.id}>
              <td className="govuk-table__cell">{s.id}</td>
              <td className="govuk-table__cell">{s.type}</td>
              <td className="govuk-table__cell">
                <a className="govuk-link" href={s.url} target="_blank" rel="noreferrer">
                  {s.url}
                </a>
              </td>
              <td className="govuk-table__cell">{s.tags.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
