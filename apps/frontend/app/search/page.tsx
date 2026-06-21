"use client";

import { useState } from "react";
import { api, QueryResultItem } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<QueryResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.query(query);
      setItems(res.items);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Search</h1>
      <form onSubmit={runSearch} style={{ display: "flex", gap: "0.5rem" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search indexed content..."
          style={{
            flex: 1,
            padding: "0.6rem",
            borderRadius: 6,
            border: "1px solid #334155",
            background: "#1e293b",
            color: "#e2e8f0",
          }}
        />
        <button
          type="submit"
          style={{
            padding: "0.6rem 1rem",
            borderRadius: 6,
            border: "none",
            background: "#2563eb",
            color: "white",
            cursor: "pointer",
          }}
        >
          Search
        </button>
      </form>

      {loading && <p>Searching...</p>}
      {error && <p style={{ color: "#fca5a5" }}>{error}</p>}

      <div style={{ marginTop: "1.5rem", display: "grid", gap: "1rem" }}>
        {items.map((it) => (
          <div
            key={it.chunk_id}
            style={{
              padding: "1rem",
              borderRadius: 8,
              background: "#1e293b",
              border: "1px solid #334155",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{it.title ?? it.source_id}</strong>
              <span style={{ color: "#64748b" }}>score {it.score.toFixed(2)}</span>
            </div>
            <p style={{ color: "#cbd5e1" }}>{it.snippet}</p>
            {it.url && (
              <a href={it.url} style={{ color: "#93c5fd" }} target="_blank">
                {it.url}
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
