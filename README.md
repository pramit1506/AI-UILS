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
- **Review Queue & Confidence Badging**: Flags low-confidence extractions (`< 0.70`) for human-in-the-loop review with quick-action review workflows.
- **Universal Search & Dashboard**: Full-text and schema-filtered search over historical log records stored in PostgreSQL (JSONB).
- **Flexible LLM Provider Support**: Native integration with Groq, Cerebras , Gemini and OpenRouter for ultra-fast cloud inference and Ollama for fully local, private offline inference.
- **Document & File Intake**: Supports text, paste, email, and document parsing with source attribution.

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
- **Groq Cloud / Ollama** (LLM Providers)
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

## Installation & Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** & **npm**
- **PostgreSQL 15+** (or Docker)
- **Groq API Key** (or local **Ollama** installation)

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
   GROQ_API_KEY="your-groq-api-key-here"
   DEFAULT_MODEL="qwen/qwen3.6-27b"
   LLM_PROVIDER="groq"
   SECRET_KEY="your-secret-key-min-32-chars-long"
   ```

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
   npm install
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

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health/` | `GET` | Health check and system metadata |
| `/api/v1/chat/` | `POST` | Process multi-turn conversational message and update draft |
| `/api/v1/logs/` | `GET` | List saved log records with optional filtering |
| `/api/v1/logs/search` | `GET` | Full-text search across log records |
| `/api/v1/logs/{log_reference}` | `GET` | Retrieve specific log record by reference |
| `/api/v1/logs/{log_reference}/review` | `PATCH` | Mark a log record as reviewed |
| `/api/v1/upload/` | `POST` | Upload and parse document file |
| `/api/v1/system-logs/` | `GET` | Retrieve system execution telemetry |

---

## License

This project is licensed under the MIT License.