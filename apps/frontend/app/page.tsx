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
      <h1>Dashboard</h1>
      <p style={{ color: "#94a3b8" }}>
        Configured ingestion sources. Use Search to explore indexed content and
        Reports to generate a briefing.
      </p>

      {error && (
        <p style={{ color: "#fca5a5" }}>
          Could not load sources (is the API running?): {error}
        </p>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "1rem" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "1px solid #1e293b" }}>
            <th style={{ padding: "0.5rem" }}>ID</th>
            <th style={{ padding: "0.5rem" }}>Type</th>
            <th style={{ padding: "0.5rem" }}>URL</th>
            <th style={{ padding: "0.5rem" }}>Tags</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => (
            <tr key={s.id} style={{ borderBottom: "1px solid #1e293b" }}>
              <td style={{ padding: "0.5rem" }}>{s.id}</td>
              <td style={{ padding: "0.5rem" }}>{s.type}</td>
              <td style={{ padding: "0.5rem", color: "#93c5fd" }}>{s.url}</td>
              <td style={{ padding: "0.5rem" }}>{s.tags.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
