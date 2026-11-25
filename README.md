# AI-Powered Universal Information Logging System (AI-UILS)

A high-performance, domain-agnostic AI assistant and data capture platform that extracts structured information from unstructured text, documents, and natural language conversations, populating real-time editable records and persisting them into a flexible ledger.

---

## Overview

Traditional intake systems are rigid and bound to predefined schemas. **AI-UILS** is built to dynamically understand any document or unstructured input—such as invoices, medical records, resumes, contracts, incident reports, receipts, and customer inquiries—extract structured key-value pairs with confidence scoring, validate data integrity, and support interactive conversational refinement.

---

## Core Capabilities

- **Dynamic Entity Extraction**: Automatically infers document domains and schemas, extracting structured fields with per-field confidence scores.
- **Real-Time Interactive Drafts**: Live-synced editable log drafts on the frontend React UI as the user converses with the AI assistant.
- **Conversational Refinement & Editing**: Update, correct, or add fields conversationally (e.g., *"Change invoice total to $500"* or *"Add vendor address"*).
- **Proactive Clarification Engine**: The AI detects missing critical information and prompts the user with targeted questions.
- **Review Queue & Confidence Badging**: Flags low-confidence extractions (`< 0.75`) for human-in-the-loop review with quick-action review workflows.
- **Document search** searches a signed-in user's saved fields, summaries, filenames and retained source text using an inverted index in PostgreSQL.
- **Flexible LLM Provider Support**: Gemini-first routing with Groq and OpenRouter fallbacks, plus local inference through Ollama.
- **Document intake and review**: Upload PDF, DOCX, TXT, or EML files, paste text, or try a built-in sample. Review the proposed fields alongside the original and sign in to save a record.
- **Account and workspace settings**: Reset a forgotten password with an emailed code. Choose a palette, display mode, and search preference.

---

## Technology Stack

### Frontend
- **React 18** with **TypeScript**
- **Redux Toolkit** for predictable centralized state management
- **Vite** for build tooling
- **Lucide React** for UI icons
- **Vitest** & **React Testing Library** for frontend testing

### Backend
- **FastAPI** (Asynchronous Python Web Framework)
- **LangGraph** (Stateful AI Agent Workflow & Decision Orchestration)
- **LiteLLM** for Gemini, Groq, and OpenRouter routing, with an Ollama option for local inference
- **PostgreSQL 15+** with JSONB & GIN indexing for flexible schemas
- **SQLAlchemy 2.0 (Asyncpg)** & **Alembic** for migrations
- **Pydantic v2** for validation and data contracts

---

## System Architecture

```text
AI-UILS/
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/v1/           # REST endpoints (chat, logs, upload, health)
│   │   ├── core/             # Configuration, settings, and logging
│   │   ├── database/         # SQLAlchemy session & Base model definitions
│   │   ├── graph/            # LangGraph agent state, nodes, routing, workflows
│   │   ├── llm/              # LLM provider abstractions (Groq, Ollama)
│   │   ├── models/           # SQLAlchemy ORM models (LogRecord)
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic schemas (Draft, Chat, Memory, LogRecord)
│   │   ├── services/         # Business logic (DraftService, MemoryService, DecisionService)
│   │   ├── tools/            # Tool implementations (save_log, edit_log, summarize_log, search_logs)
│   │   └── utils/            # Helper utilities and formatters
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/       # UI components (Chat, LogForm, Dashboard, Layout)
│   │   ├── hooks/            # Custom React hooks (shortcuts, review workflows)
│   │   ├── redux/            # Redux slices (chat, log, agent, document)
│   │   ├── services/         # API client & response mappers
│   │   └── types/            # TypeScript interfaces
│   ├── tests/                # Frontend test suites
│   └── package.json
│
├── docs/                     # Technical specifications & API docs
├── docker-compose.yml        # Multi-container deployment setup
└── README.md
```

---

## LangGraph Agent Workflow

```text
               ┌────────────────────────┐
               │    User Message /      │
               │   Document Intake      │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │       input_node       │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │       intent_node      │
               └───────────┬────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     [logging / update]           [conversation]
              │                         │
              ▼                         │
   ┌───────────────────────┐            │
   │ entity_extraction_node│            │
   └──────────┬────────────┘            │
              │                         │
              ▼                         │
   ┌───────────────────────┐            │
   │     decision_node     │            │
   └──────────┬────────────┘            │
              │                         │
     ┌────────┴────────┬────────┐       │
     │                 │        │       │
 [CLARIFY]     [EXECUTE_TOOL] [RESPOND] │
     │                 │        │       │
     │                 ▼        │       │
     │      ┌─────────────────┐ │       │
     │      │tool_selection_n.│ │       │
     │      └────────┬────────┘ │       │
     │               │          │       │
     │               ▼          │       │
     │      ┌─────────────────┐ │       │
     │      │tool_execution_n.│ │       │
     │      └────────┬────────┘ │       │
     │               │          │       │
     └───────────────┼──────────┘       │
                     ▼                  │
            ┌─────────────────┐         │
            │  response_node  │◄────────┘
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   Final State   │
            │   & UI Update   │
            └─────────────────┘
```

---

## Searching saved documents

Open **Saved records** and type in the search field. Results update after a short pause. Each word can match anywhere in the record, including the saved document text. Use the review queue to restrict results to records awaiting review. Expand a result and choose **View saved text** to read its source when available.

Related search matches words, prefixes and English synonyms. Choose **Exact words only** in Settings for precise reference lookups. Both modes ignore case according to the database locale and split punctuation. Results are ordered newest first. PostgreSQL indexes and cursor pagination serve each page without model calls.

Saving a document in the editor retains its extracted text and filename with the record. Older records are indexed from the information that was actually saved. Image-only scans require OCR before they can contribute searchable text.

For an Alembic-managed installation, run `alembic upgrade head` from `backend` before deploying this version. The new revision builds the search terms and indexes existing records. Plan a maintenance window for a populated ledger because this migration rewrites the table and builds its indexes. For an older installation without a migration stamp, validate its schema on a restored copy first. The startup bootstrap also handles the previous create-all layout.

See the [database notes](docs/database.md) for storage and migration details and the [verification notes](docs/verification.md) for tested workflows and scope.

## Installation & Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 22.12+** & **npm**. Node.js 20.19+ on the 20.x line also works.
- **PostgreSQL 15+** (or Docker)
- **Gemini, Groq or OpenRouter API key** for cloud inference, or a local **Ollama** installation

---

### 1. Backend Setup

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   copy .env.example .env   # Windows
   cp .env.example .env     # Linux / macOS
   ```

   Update `.env` with your settings:
   ```env
   PROJECT_NAME="AI-Powered Universal Information Logging System"
   DATABASE_URL="postgresql+asyncpg://username:password@localhost:5432/database_name"
   GROQ_API_KEY=
   GEMINI_API_KEY_1=
   OPENROUTER_API_KEY_1=
   LLM_PROVIDER="multi"
   SECRET_KEY="your-secret-key-min-32-chars-long"
   ```

   Generate a unique signing key with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   Enter credentials only in the private backend environment or the project-root
   `.env` for Docker Compose. Uncomment and fill the provider slots you use. In multi-provider mode the order is Gemini, Groq,
   then OpenRouter. Flash handles document extraction and Flash-Lite handles
   intent and compression. Flash-Lite also backs up extraction if Flash is unavailable. Groq uses Qwen 3.8 27B and GPT-OSS 20B for those
   roles respectively. OpenRouter uses explicitly free Gemma models and Particle-1 as a final fallback, with a zero
   maximum price per input token, output token and request.

   Check every configured Gemini project's plan in Google AI Studio and every
   Groq organization's plan in Groq Console. Set `GEMINI_FREE_TIER_CONFIRMED`
   and/or `GROQ_FREE_TIER_CONFIRMED` to `true` only for verified free accounts.
   Recheck when replacing keys or changing billing plans. Keys in the same
   project or organization can share quotas.
   Local inference is available with `LLM_PROVIDER=ollama`.

   > The server refuses to start (when `DEBUG=False`) if `SECRET_KEY` is still
   > an insecure default, and demo accounts are only seeded when `DEBUG=True`.

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   API Docs available at: `http://127.0.0.1:8000/docs`

---

### 2. Frontend Setup

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm ci
   ```

3. Start the development server:
   ```bash
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

4. Open the application:
   ```
   http://127.0.0.1:5173
   ```

---

## Running with Docker Compose

To spin up the entire system (PostgreSQL, FastAPI Backend, and React Frontend) with Docker:

Compose reads the private `backend/.env` and optional root `.env`. Set a strong
`SECRET_KEY` before starting. The published ports listen on loopback. For local
HTTP browser testing, set `AUTH_COOKIE_SECURE=false` in the private environment.
For any deployment behind an HTTPS reverse proxy use `AUTH_COOKIE_SECURE=true`.
The backend keeps its conversation database in `backend/data`.

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

---

## Testing

### Frontend Tests
Run unit and integration tests using Vitest:
```bash
cd frontend
npm test -- --run
```

### Backend Tests
Run backend test suite using pytest:
```bash
cd backend
pytest
```

---

## API Summary

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/health` | `GET` | No | Health check |
| `/api/v1/ready` | `GET` | No | Database readiness, returns 503 during a database outage |
| `/api/v1/auth/register` | `POST` | No | Create an account (role is always server-assigned) |
| `/api/v1/auth/login` | `POST` | No | Sign in and obtain a JWT access token |
| `/api/v1/auth/me` | `GET` | JWT | Current user profile |
| `/api/v1/auth/profile` | `PUT` | JWT | Update profile details |
| `/api/v1/auth/reset-password` | `POST` | JWT | Change password (requires current password) |
| `/api/v1/auth/recovery/status` | `GET` | No | Report whether recovery email is configured |
| `/api/v1/auth/recovery/request` | `POST` | No | Request a password reset code for an eligible account |
| `/api/v1/auth/recovery/confirm` | `POST` | No | Reset a password with a valid one-time code |
| `/api/v1/auth/logout` | `POST` | Cookie session | Clear browser authentication cookies |
| `/api/v1/auth/account` | `DELETE` | JWT | Delete the authenticated account and its logs |
| `/api/v1/chat/` | `POST` | Optional | Capture, chat, or save a reviewed record. Saving requires sign-in. |
| `/api/v1/logs/` | `GET` | JWT | List the authenticated user's log records with optional filtering |
| `/api/v1/logs/search` | `GET` | JWT | Search by `q`, optional `schema_name` and `needs_review`, and page using `next_cursor` as `cursor` |
| `/api/v1/logs/{log_reference}/source` | `GET` | JWT | Read the saved source text of an owned record |
| `/api/v1/logs/{log_reference}` | `GET` | JWT | Retrieve a specific log record by reference |
| `/api/v1/logs/{log_reference}` | `PATCH` | JWT | Edit an owned record |
| `/api/v1/logs/{log_reference}/review` | `PATCH` | JWT | Mark one of the user's log records as reviewed |
| `/api/v1/logs/{log_reference}` | `DELETE` | JWT | Delete the user's log record |
| `/api/v1/upload/extract-text` | `POST` | JWT | Upload and parse document file (max 10 MiB) |
| `/api/v1/system-logs/` | `POST` | JWT | Submit frontend error telemetry for ingestion |

Signed-out users can request a six-digit email code through **Forgot password**.
Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, and your mail provider's credentials
in the private backend environment. Port 587 uses STARTTLS. Set `SMTP_IMPLICIT_TLS=true`
for implicit TLS on port 465. Codes expire after ten minutes and are consumed on success. The sign-in screen shows when recovery email is disabled. Use a dummy account with a mailbox you control to verify delivery after configuring a new host.
Changing a password invalidates earlier sessions.

Run `alembic upgrade head` before deployment. The workspace revision creates the recovery
columns and builds an additional GIN index on existing documents. Schedule the index
build during a maintenance window on a populated installation.

Saved-record search updates as you type. Related search combines exact words,
alphanumeric prefixes of at least three characters, and an offline English synonym dictionary
derived from WordNet. The short topic list supplements common cross-domain labels.
Exact words mode is available in Settings. Both modes use the owner's records and
cursor pagination. The bundled dictionary includes its [license](backend/app/search_data/WORDNET-LICENSE.txt).

## Repository hygiene

The checked-in environment templates contain placeholders. Keep populated
environment files, provider keys, signing keys, SMTP credentials, uploads,
database files, and logs in your local environment. Use fictional documents
and accounts in tests and public bug reports. The app can send document text
to the configured inference provider. Use Ollama when inference must run locally.

---

## License

This project is licensed under the [MIT License](LICENSE).
