export const metadata = {
  title: "WebFeedReports",
  description: "RSS & web briefing platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </head>
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          margin: 0,
          background: "#0f172a",
          color: "#e2e8f0",
        }}
      >
        <header
          style={{
            padding: "1rem 2rem",
            borderBottom: "1px solid #1e293b",
            display: "flex",
            gap: "1.5rem",
            alignItems: "center",
          }}
        >
          <strong style={{ fontSize: "1.1rem" }}>WebFeedReports</strong>
          <nav style={{ display: "flex", gap: "1rem" }}>
            <a href="/" style={{ color: "#93c5fd" }}>
              Dashboard
            </a>
            <a href="/search" style={{ color: "#93c5fd" }}>
              Search
            </a>
            <a href="/reports" style={{ color: "#93c5fd" }}>
              Reports
            </a>
          </nav>
        </header>
        <main style={{ padding: "2rem", maxWidth: 960, margin: "0 auto" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
