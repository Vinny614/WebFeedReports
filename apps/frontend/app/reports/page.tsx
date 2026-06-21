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
      <h1>Generate Briefing Report</h1>
      <p style={{ color: "#94a3b8" }}>
        Submit a request and the report will be generated and displayed here
        automatically when it&apos;s ready.
      </p>

      <form onSubmit={submit} style={{ display: "grid", gap: "0.75rem", maxWidth: 520 }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Report title (optional)"
          style={inputStyle}
          disabled={busy}
        />
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What should the briefing cover?"
          rows={4}
          style={inputStyle}
          disabled={busy}
        />
        <button type="submit" style={buttonStyle} disabled={busy || !query.trim()}>
          {busy ? "Generating…" : "Generate Report"}
        </button>
      </form>

      {busy && (
        <div style={statusBox}>
          <span style={spinnerStyle} aria-hidden />
          <span>
            {phase === "submitting"
              ? "Submitting request…"
              : `Generating report (status: ${status})…`}
          </span>
        </div>
      )}

      {error && <p style={{ color: "#fca5a5", marginTop: "1rem" }}>Error: {error}</p>}

      {report && <ReportView report={report} />}
    </div>
  );
}

function ReportView({ report }: { report: BriefingReport }) {
  return (
    <article style={reportCard}>
      <h2 style={{ marginBottom: "0.25rem" }}>{report.title}</h2>
      <p style={{ color: "#64748b", fontSize: "0.85rem", marginTop: 0 }}>
        Generated {new Date(report.generated_at).toLocaleString()} · query: “{report.query}”
      </p>

      <h3 style={sectionHeading}>Summary</h3>
      <p style={{ lineHeight: 1.6 }}>{report.summary}</p>

      {report.sections.map((s, i) => (
        <section key={i}>
          <h3 style={sectionHeading}>{s.heading}</h3>
          <p style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{s.content}</p>
        </section>
      ))}

      {report.citations.length > 0 && (
        <>
          <h3 style={sectionHeading}>Sources</h3>
          <ul style={{ paddingLeft: "1.1rem", lineHeight: 1.7 }}>
            {report.citations.map((c, i) => (
              <li key={i}>
                {c.url ? (
                  <a href={c.url} target="_blank" rel="noreferrer" style={{ color: "#93c5fd" }}>
                    {c.title || c.url}
                  </a>
                ) : (
                  <span>{c.title || c.source_id}</span>
                )}
                <span style={{ color: "#64748b" }}> — {c.source_id}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </article>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "0.6rem",
  borderRadius: 6,
  border: "1px solid #334155",
  background: "#1e293b",
  color: "#e2e8f0",
};

const buttonStyle: React.CSSProperties = {
  padding: "0.6rem 1rem",
  borderRadius: 6,
  border: "none",
  background: "#2563eb",
  color: "white",
  cursor: "pointer",
};

const statusBox: React.CSSProperties = {
  marginTop: "1.5rem",
  display: "flex",
  alignItems: "center",
  gap: "0.6rem",
  color: "#94a3b8",
};

const spinnerStyle: React.CSSProperties = {
  width: 16,
  height: 16,
  border: "2px solid #334155",
  borderTopColor: "#2563eb",
  borderRadius: "50%",
  display: "inline-block",
  animation: "spin 0.8s linear infinite",
};

const reportCard: React.CSSProperties = {
  marginTop: "1.5rem",
  padding: "1.25rem 1.5rem",
  borderRadius: 8,
  background: "#0f172a",
  border: "1px solid #1e293b",
};

const sectionHeading: React.CSSProperties = {
  marginTop: "1.25rem",
  marginBottom: "0.4rem",
  color: "#e2e8f0",
  borderBottom: "1px solid #1e293b",
  paddingBottom: "0.25rem",
};
