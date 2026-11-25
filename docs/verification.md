# Verification

The production frontend build and the live sandbox were verified with fictional documents and disposable accounts. The sandbox used FastAPI, PostgreSQL, real provider calls on the configured free plans, and a local SMTP receiver with STARTTLS.

- **Capture and review** cover PDF, DOCX, TXT, and EML parsing, Word tables and encoded email, field edits, bulk review, original text, and click-to-save.
- **Search** covers owner isolation, exact and related matches, alphanumeric prefixes, source-only terms, result paging, and live search in the browser.
- **Accounts and browsers** cover guest-to-account draft handoff, settings, profile changes, and OTP reset. Chrome, Firefox, and WebKit completed registration, save, settings, and recovery over sandbox HTTPS.
- **Deployment** checks covered the live Nginx and Docker Compose stack. Readiness returned 503 with PostgreSQL stopped and 200 after recovery.

The combined live run recorded 48 passing checks. With 10,000 synthetic records, a focused loopback test of 64 search requests at concurrency eight measured a p95 of 212 ms. These are sandbox measurements. External SMTP delivery, native mobile devices, screen readers, and production load require separate verification.
