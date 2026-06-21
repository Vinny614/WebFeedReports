import "./globals.css";

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
      <body>
        <a href="#main-content" className="govuk-skip-link">
          Skip to main content
        </a>

        <header className="govuk-header" role="banner">
          <div className="govuk-header__container">
            <a href="/" className="govuk-header__logo">
              WebFeedReports
            </a>
            <nav className="govuk-header__nav" aria-label="Menu">
              <a href="/" className="govuk-header__link">
                Dashboard
              </a>
              <a href="/search" className="govuk-header__link">
                Search
              </a>
              <a href="/reports" className="govuk-header__link">
                Reports
              </a>
            </nav>
          </div>
        </header>

        <div className="govuk-width-container">
          <div className="govuk-phase-banner">
            <p className="govuk-phase-banner__content">
              <strong className="govuk-tag">Beta</strong>
              <span>
                This is a new service — your feedback will help us to improve it.
              </span>
            </p>
          </div>

          <main className="govuk-main-wrapper" id="main-content" role="main">
            {children}
          </main>
        </div>

        <footer className="govuk-footer" role="contentinfo">
          <div className="govuk-footer__container">
            <p className="govuk-body-s govuk-!-margin-bottom-0">
              WebFeedReports — RSS &amp; web briefing platform.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
