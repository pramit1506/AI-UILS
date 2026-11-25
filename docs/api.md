# HTTP API

FastAPI serves interactive documentation at `/docs` on the backend and OpenAPI at `/api/v1/openapi.json`. Endpoints are listed in the [README](../README.md#api-summary).

## Authentication

Registration and login set an HTTP-only session cookie and a readable CSRF cookie for the web app. Cookie-authenticated writes include the CSRF value in the `X-CSRF-Token` header. API clients can use the bearer token returned at sign-in. Password changes and recovery invalidate previous tokens.

Signed-out visitors can capture a temporary draft and use the conversation. Uploading files, saving records, and reading saved records require authentication.

## Capture and search

- `POST /api/v1/upload/extract-text` accepts a multipart PDF, DOCX, TXT, or EML file up to 10 MiB and returns its filename and extracted text. The route parses text-based PDFs, Word paragraphs and tables, and decoded email bodies.
- `POST /api/v1/chat/` accepts `capture`, `chat`, or `save_reviewed`. Carry the returned conversation ID into follow-up requests. The result indicates when local extraction generated a fallback draft.
- `GET /api/v1/logs/search` takes `q`, optional `schema_name` and `needs_review`, `related`, and a limit up to 50. Pass the returned `next_cursor` as `cursor` to read the next page with the same filters.
- `GET /api/v1/logs/{log_reference}/source` returns retained source text and its filename when available. The details, edit, review, and delete routes all use the public record reference.

Database readiness reports HTTP 200 when the database responds and HTTP 503 when it is unavailable.
