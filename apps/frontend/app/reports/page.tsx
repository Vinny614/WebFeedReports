"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function ReportsPage() {
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setJobId(null);
    try {
      const res = await api.submitReport(query, title || undefined);
      setJobId(res.job_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <h1>Generate Briefing Report</h1>
      <p style={{ color: "#94a3b8" }}>
        Report generation is asynchronous. Submit a request and poll the returned
        job id for status.
      </p>

      <form onSubmit={submit} style={{ display: "grid", gap: "0.75rem", maxWidth: 520 }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Report title (optional)"
          style={inputStyle}
        />
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What should the briefing cover?"
          rows={4}
          style={inputStyle}
        />
        <button type="submit" style={buttonStyle}>
          Submit Report Request
        </button>
      </form>

      {error && <p style={{ color: "#fca5a5" }}>{error}</p>}
      {jobId && (
        <div
          style={{
            marginTop: "1.5rem",
            padding: "1rem",
            borderRadius: 8,
            background: "#1e293b",
            border: "1px solid #334155",
          }}
        >
          <p>
            Report job submitted. Job id: <code>{jobId}</code>
          </p>
          <p style={{ color: "#94a3b8" }}>
            Poll <code>GET /jobs/report/{jobId}</code> for status, then fetch the
            report at <code>GET /reports/&lt;report_id&gt;</code>.
          </p>
        </div>
      )}
    </div>
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
