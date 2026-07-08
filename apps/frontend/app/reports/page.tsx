"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  BriefingReport,
  JobStatus,
  RecentHeadingSet,
  ReportTemplate,
  ReportTemplateSection,
} from "@/lib/api";

type Phase = "idle" | "submitting" | "working" | "done" | "error";

const CUSTOM = "custom";

const COMPANY_FILTERS: { id: string; label: string }[] = [
  { id: "airbus-press", label: "Airbus" },
  { id: "leonardo-press", label: "Leonardo" },
  { id: "boeing-press", label: "Boeing" },
];

const TOPIC_FILTERS: { id: string; label: string }[] = [
  { id: "defence", label: "Defence" },
  { id: "aviation-safety", label: "Aviation safety" },
  { id: "regulation", label: "Regulation" },
  { id: "arms-sales", label: "Arms sales" },
  { id: "arms-transfers", label: "Arms transfers" },
  { id: "business", label: "Business" },
  { id: "security", label: "Security" },
];

function dayStart(d: string): string | null {
  return d ? `${d}T00:00:00Z` : null;
}
function dayEnd(d: string): string | null {
  return d ? `${d}T23:59:59Z` : null;
}

function blankSection(): ReportTemplateSection {
  return { heading: "", style: "items", guidance: "", query: null, tags: [] };
}

function cloneSections(
  sections: ReportTemplateSection[]
): ReportTemplateSection[] {
  return sections.map((s) => ({
    heading: s.heading,
    style: s.style,
    guidance: s.guidance ?? "",
    query: s.query ?? null,
    tags: [...(s.tags ?? [])],
  }));
}

export default function ReportsPage() {
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [recents, setRecents] = useState<RecentHeadingSet[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>(CUSTOM);
  const [sections, setSections] = useState<ReportTemplateSection[]>([
    blankSection(),
  ]);
  // Tracks whether the headings differ from the selected built-in template, so
  // that unmodified templates run server-side and only edited/custom heading
  // sets are recorded to the "recent headings" store.
  const [dirty, setDirty] = useState(true);

  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [report, setReport] = useState<BriefingReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [t, r] = await Promise.all([
          api.listReportTemplates(),
          api.listRecentHeadings(),
        ]);
        setTemplates(t);
        setRecents(r);
      } catch {
        // Non-fatal: the builder still works in custom mode.
      }
    })();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function applyTemplate(id: string) {
    setSelectedTemplateId(id);
    if (id === CUSTOM) {
      setSections([blankSection()]);
      setDirty(true);
      return;
    }
    const tpl = templates.find((t) => t.id === id);
    if (!tpl) return;
    setSections(cloneSections(tpl.sections));
    setDirty(false);
    if (!title.trim()) setTitle(tpl.name);
    if (!query.trim() && tpl.default_query) setQuery(tpl.default_query);
  }

  function applyRecent(index: number) {
    const set = recents[index];
    if (!set) return;
    setSelectedTemplateId(CUSTOM);
    setSections(cloneSections(set.sections));
    setDirty(true);
    if (set.name && !title.trim()) setTitle(set.name);
  }

  function updateSection(i: number, patch: Partial<ReportTemplateSection>) {
    setSections((prev) =>
      prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s))
    );
    setDirty(true);
  }

  function addSection() {
    setSections((prev) => [...prev, blankSection()]);
    setDirty(true);
  }

  function removeSection(i: number) {
    setSections((prev) => prev.filter((_, idx) => idx !== i));
    setDirty(true);
  }

  function moveSection(i: number, dir: -1 | 1) {
    setSections((prev) => {
      const next = [...prev];
      const j = i + dir;
      if (j < 0 || j >= next.length) return prev;
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
    setDirty(true);
  }

  function toggleSource(id: string) {
    setSelectedSources((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  }

  function toggleTopic(id: string) {
    setSelectedTopics((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    stopPolling();
    setError(null);
    setReport(null);
    setStatus(null);
    setPhase("submitting");

    const cleaned = sections
      .map((s) => ({ ...s, heading: s.heading.trim() }))
      .filter((s) => s.heading.length > 0);

    const usingTemplate = selectedTemplateId !== CUSTOM && !dirty;

    try {
      const { job_id } = await api.submitReport({
        query,
        title: title || undefined,
        source_ids: selectedSources,
        tags: selectedTopics,
        date_from: dayStart(dateFrom),
        date_to: dayEnd(dateTo),
        template_id: selectedTemplateId === CUSTOM ? null : selectedTemplateId,
        sections: usingTemplate ? null : cleaned,
      });
      setPhase("working");
      setStatus("queued");

      // Poll the job until it completes, then fetch and display the report.
      pollRef.current = setInterval(async () => {
        try {
          const job = await api.getReportJob(job_id);
          setStatus(job.status);

          if (job.status === "succeeded" && job.result_ref) {
            stopPolling();
            const rep = await api.getReport(job.result_ref);
            setReport(rep);
            setPhase("done");
            // Refresh recents so a newly-saved custom set appears.
            api
              .listRecentHeadings()
              .then(setRecents)
              .catch(() => undefined);
          } else if (job.status === "failed") {
            stopPolling();
            setError(job.error || "Report generation failed.");
            setPhase("error");
          }
        } catch (err) {
          stopPolling();
          setError((err as Error).message);
          setPhase("error");
        }
      }, 2500);
    } catch (err) {
      setError((err as Error).message);
      setPhase("error");
    }
  }

  const busy = phase === "submitting" || phase === "working";
  const hasHeadings = sections.some((s) => s.heading.trim().length > 0);

  return (
    <div>
      <h1 className="govuk-heading-xl">Generate briefing report</h1>
      <p className="govuk-body">
        Pick a template or define your own headings. The report is built section
        by section and displayed here when it&apos;s ready.
      </p>

      <form onSubmit={submit}>
        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor="report-template">
            Template
          </label>
          <select
            id="report-template"
            className="govuk-select"
            value={selectedTemplateId}
            onChange={(e) => applyTemplate(e.target.value)}
            disabled={busy}
          >
            <option value={CUSTOM}>Custom (define your own headings)</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>

        {recents.length > 0 && (
          <div className="govuk-form-group">
            <label className="govuk-label" htmlFor="report-recent">
              Recent headings
            </label>
            <select
              id="report-recent"
              className="govuk-select"
              defaultValue=""
              onChange={(e) => {
                if (e.target.value !== "") applyRecent(Number(e.target.value));
                e.target.value = "";
              }}
              disabled={busy}
            >
              <option value="">Reuse a recent heading set…</option>
              {recents.map((r, i) => (
                <option key={i} value={i}>
                  {(r.name || "Untitled") +
                    " — " +
                    r.sections.map((s) => s.heading).join(", ")}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor="report-title">
            Report title (optional)
          </label>
          <input
            id="report-title"
            className="govuk-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={busy}
          />
        </div>

        <div className="govuk-form-group">
          <label className="govuk-label" htmlFor="report-query">
            Overall topic / focus
          </label>
          <textarea
            id="report-query"
            className="govuk-textarea"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={2}
            disabled={busy}
          />
        </div>

        <details className="govuk-details" open>
          <summary className="govuk-details__summary">
            <span className="govuk-details__summary-text">
              Filters (date range, companies &amp; topics)
            </span>
          </summary>
          <div className="govuk-details__text">
            <div className="app-filter-grid">
              <div className="govuk-form-group">
                <label className="govuk-label" htmlFor="report-date-from">
                  From date
                </label>
                <input
                  id="report-date-from"
                  type="date"
                  className="govuk-input"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  disabled={busy}
                />
              </div>
              <div className="govuk-form-group">
                <label className="govuk-label" htmlFor="report-date-to">
                  To date
                </label>
                <input
                  id="report-date-to"
                  type="date"
                  className="govuk-input"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  disabled={busy}
                />
              </div>
            </div>

            <fieldset className="govuk-fieldset">
              <legend className="govuk-fieldset__legend">
                Restrict to companies (optional)
              </legend>
              <div className="govuk-checkboxes govuk-checkboxes--small app-checkbox-grid">
                {COMPANY_FILTERS.map((c) => (
                  <div key={c.id} className="govuk-checkboxes__item">
                    <input
                      className="govuk-checkboxes__input"
                      id={`report-src-${c.id}`}
                      type="checkbox"
                      checked={selectedSources.includes(c.id)}
                      onChange={() => toggleSource(c.id)}
                      disabled={busy}
                    />
                    <label
                      className="govuk-label govuk-checkboxes__label"
                      htmlFor={`report-src-${c.id}`}
                    >
                      {c.label}
                    </label>
                  </div>
                ))}
              </div>
            </fieldset>

            <fieldset className="govuk-fieldset">
              <legend className="govuk-fieldset__legend">
                Restrict to topics (optional)
              </legend>
              <div className="govuk-checkboxes govuk-checkboxes--small app-checkbox-grid">
                {TOPIC_FILTERS.map((t) => (
                  <div key={t.id} className="govuk-checkboxes__item">
                    <input
                      className="govuk-checkboxes__input"
                      id={`report-topic-${t.id}`}
                      type="checkbox"
                      checked={selectedTopics.includes(t.id)}
                      onChange={() => toggleTopic(t.id)}
                      disabled={busy}
                    />
                    <label
                      className="govuk-label govuk-checkboxes__label"
                      htmlFor={`report-topic-${t.id}`}
                    >
                      {t.label}
                    </label>
                  </div>
                ))}
              </div>
            </fieldset>
          </div>
        </details>

        <fieldset className="govuk-fieldset">
          <legend className="govuk-fieldset__legend govuk-fieldset__legend--m">
            Headings
          </legend>
          {sections.map((s, i) => (
            <div key={i} className="app-heading-row">
              <div className="app-heading-row__main">
                <input
                  className="govuk-input"
                  placeholder="Heading (e.g. Middle East)"
                  value={s.heading}
                  onChange={(e) =>
                    updateSection(i, { heading: e.target.value })
                  }
                  disabled={busy}
                />
                <select
                  className="govuk-select"
                  aria-label={`Section ${i + 1} style`}
                  value={s.style}
                  onChange={(e) =>
                    updateSection(i, {
                      style: e.target.value as "narrative" | "items",
                    })
                  }
                  disabled={busy}
                >
                  <option value="items">News items</option>
                  <option value="narrative">Narrative</option>
                </select>
              </div>
              <input
                className="govuk-input app-heading-row__guidance"
                placeholder="Guidance (optional) — what this section should cover"
                value={s.guidance ?? ""}
                onChange={(e) => updateSection(i, { guidance: e.target.value })}
                disabled={busy}
              />
              <div className="app-heading-row__controls">
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary"
                  onClick={() => moveSection(i, -1)}
                  disabled={busy || i === 0}
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="govuk-button govuk-button--secondary"
                  onClick={() => moveSection(i, 1)}
                  disabled={busy || i === sections.length - 1}
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="govuk-button govuk-button--warning"
                  onClick={() => removeSection(i)}
                  disabled={busy || sections.length === 1}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          <button
            type="button"
            className="govuk-button govuk-button--secondary"
            onClick={addSection}
            disabled={busy}
          >
            Add heading
          </button>
        </fieldset>

        <button
          type="submit"
          className="govuk-button"
          disabled={busy || !query.trim() || !hasHeadings}
        >
          {busy ? "Generating…" : "Generate report"}
        </button>
      </form>

      {busy && (
        <div className="app-status" role="status" aria-live="polite">
          <span className="app-spinner" aria-hidden="true" />
          <span>
            {phase === "submitting"
              ? "Submitting request…"
              : `Generating report (status: ${status})…`}
          </span>
        </div>
      )}

      {error && (
        <div
          className="govuk-error-summary"
          role="alert"
          aria-labelledby="report-error-title"
        >
          <h2 className="govuk-error-summary__title" id="report-error-title">
            There is a problem
          </h2>
          <p className="govuk-body govuk-!-margin-bottom-0">{error}</p>
        </div>
      )}

      {report && <ReportView report={report} />}
    </div>
  );
}

function ReportView({ report }: { report: BriefingReport }) {
  return (
    <article aria-live="polite">
      <hr className="app-section-break" />
      <h2 className="govuk-heading-l">{report.title}</h2>
      <p className="govuk-caption-m">
        Generated {new Date(report.generated_at).toLocaleString()} · query: “
        {report.query}”
      </p>

      {report.summary && (
        <>
          <h3 className="govuk-heading-m">Summary</h3>
          <p className="govuk-body app-preserve-whitespace">{report.summary}</p>
        </>
      )}

      {report.sections.map((s, i) => (
        <section key={i}>
          <h3 className="govuk-heading-m">{s.heading}</h3>
          {s.style === "items" ? (
            s.items.length === 0 ? (
              <p className="govuk-body">No items found for this section.</p>
            ) : (
              <ul className="app-report-items">
                {s.items.map((it, j) => (
                  <li key={j} className="app-report-item">
                    {it.url ? (
                      <a
                        className="govuk-link app-report-item__title"
                        href={it.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {it.title}
                      </a>
                    ) : (
                      <span className="app-report-item__title">
                        {it.title}
                      </span>
                    )}
                    <p className="govuk-caption-m app-report-item__meta">
                      {it.source && <span>{it.source}</span>}
                      {it.source && it.published_at && <span> · </span>}
                      {it.published_at && (
                        <span>
                          {new Date(it.published_at).toLocaleDateString()}
                        </span>
                      )}
                      {(it.source || it.published_at) && it.url && (
                        <span> · </span>
                      )}
                      {it.url && (
                        <a
                          className="govuk-link"
                          href={it.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Read more →
                        </a>
                      )}
                    </p>
                    {it.summary && <p className="govuk-body">{it.summary}</p>}
                  </li>
                ))}
              </ul>
            )
          ) : (
            <p className="govuk-body app-preserve-whitespace">{s.content}</p>
          )}
        </section>
      ))}

      {report.citations.length > 0 && (
        <>
          <h3 className="govuk-heading-m">Sources</h3>
          <ul className="govuk-body">
            {report.citations.map((c, i) => (
              <li key={i}>
                {c.url ? (
                  <a
                    className="govuk-link"
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {c.title || c.url}
                  </a>
                ) : (
                  <span>{c.title || c.source_id}</span>
                )}
                <span className="app-source-meta"> — {c.source_id}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </article>
  );
}
