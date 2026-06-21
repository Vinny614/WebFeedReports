"use client";

import { useEffect, useRef, useState } from "react";
import { api, BriefingReport, JobStatus } from "@/lib/api";

type Phase = "idle" | "submitting" | "working" | "done" | "error";

export default function ReportsPage() {
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [report, setReport] = useState<BriefingReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clean up any in-flight polling when the component unmounts.
  useEffect(() => {
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

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    stopPolling();
    setError(null);
    setReport(null);
    setStatus(null);
    setPhase("submitting");

    try {
      const { job_id } = await api.submitReport(query, title || undefined);
      setPhase("working");
      setStatus("queued");

      // Poll the job until it completes, then fetch and display the report.
      pollRef.current = setInterval(async () => {
        try {
          const job = await api.getReportJob(job_id);
          setStatus(job.status);

          if (job.status === "succeeded" && job.result_ref) {
            stopPolling();
            const r = await api.getReport(job.result_ref);
            setReport(r);
            setPhase("done");
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

  return (
    <div>
      <h1 className="govuk-heading-xl">Generate briefing report</h1>
      <p className="govuk-body">
        Submit a request and the report will be generated and displayed here
        automatically when it&apos;s ready.
      </p>

      <form onSubmit={submit}>
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
            What should the briefing cover?
          </label>
          <textarea
            id="report-query"
            className="govuk-textarea"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            disabled={busy}
          />
        </div>

        <button
          type="submit"
          className="govuk-button"
          disabled={busy || !query.trim()}
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

      <h3 className="govuk-heading-m">Summary</h3>
      <p className="govuk-body">{report.summary}</p>

      {report.sections.map((s, i) => (
        <section key={i}>
          <h3 className="govuk-heading-m">{s.heading}</h3>
          <p className="govuk-body app-preserve-whitespace">{s.content}</p>
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
