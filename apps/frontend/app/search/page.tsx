"use client";

import { useState } from "react";
import { api, QueryResultItem } from "@/lib/api";

function dayStart(d: string): string | null {
  return d ? `${d}T00:00:00Z` : null;
}
function dayEnd(d: string): string | null {
  return d ? `${d}T23:59:59Z` : null;
}

const COMPANY_FILTERS: { id: string; label: string }[] = [
  { id: "airbus-press", label: "Airbus" },
  { id: "leonardo-press", label: "Leonardo" },
  { id: "boeing-press", label: "Boeing" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<QueryResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  function toggleSource(id: string) {
    setSelectedSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  }

  async function runSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.query(query, {
        sourceIds: selectedSources,
        dateFrom: dayStart(dateFrom),
        dateTo: dayEnd(dateTo),
      });
      setItems(res.items);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="govuk-heading-xl">Search</h1>
      <form onSubmit={runSearch}>
        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor="search-query">
            Search indexed content
          </label>
          <input
            id="search-query"
            className="govuk-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Airbus defence contract"
          />
        </div>

        <details className="govuk-details" open>
          <summary className="govuk-details__summary">
            <span className="govuk-details__summary-text">Filters</span>
          </summary>
          <div className="govuk-details__text">
            <div className="app-filter-grid">
              <div className="govuk-form-group">
                <label className="govuk-label" htmlFor="search-date-from">
                  From date
                </label>
                <input
                  id="search-date-from"
                  type="date"
                  className="govuk-input"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>
              <div className="govuk-form-group">
                <label className="govuk-label" htmlFor="search-date-to">
                  To date
                </label>
                <input
                  id="search-date-to"
                  type="date"
                  className="govuk-input"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </div>

            <fieldset className="govuk-fieldset">
              <legend className="govuk-fieldset__legend">Companies</legend>
              <div className="govuk-checkboxes govuk-checkboxes--small app-checkbox-grid">
                {COMPANY_FILTERS.map((c) => (
                  <div key={c.id} className="govuk-checkboxes__item">
                    <input
                      className="govuk-checkboxes__input"
                      id={`src-${c.id}`}
                      type="checkbox"
                      checked={selectedSources.includes(c.id)}
                      onChange={() => toggleSource(c.id)}
                    />
                    <label
                      className="govuk-label govuk-checkboxes__label"
                      htmlFor={`src-${c.id}`}
                    >
                      {c.label}
                    </label>
                  </div>
                ))}
              </div>
            </fieldset>
          </div>
        </details>

        <button type="submit" className="govuk-button" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>


      {loading && (
        <div className="app-status" role="status">
          <span className="app-spinner" aria-hidden="true" />
          <span>Searching…</span>
        </div>
      )}

      {error && (
        <div className="govuk-error-summary" role="alert" aria-labelledby="search-error-title">
          <h2 className="govuk-error-summary__title" id="search-error-title">
            There is a problem
          </h2>
          <p className="govuk-body govuk-!-margin-bottom-0">{error}</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div aria-live="polite">
          <h2 className="govuk-heading-m">
            {items.length} result{items.length === 1 ? "" : "s"}
          </h2>
          {items.map((it) => (
            <div key={it.chunk_id} className="app-card">
              <div className="app-card__header">
                <h3 className="app-card__title">{it.title ?? it.source_id}</h3>
                <span className="app-card__score">score {it.score.toFixed(2)}</span>
              </div>
              <p className="govuk-body">{it.snippet}</p>
              {it.url && (
                <a
                  className="govuk-link"
                  href={it.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {it.url}
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
