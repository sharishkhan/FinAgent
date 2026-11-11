# FinAgent: Agentic AI-Based Financial Research and Analysis Assistant

## Evidence-Based Implementation Context

**Prepared for:** Saharish Khan — CSE (AI), Roll No. 42; Tarana Thakur — CSE (AI), Roll No. 51  
**Institution:** Bhilai Institute of Technology, Durg  
**Inspection date:** 16 October 2026  
**Inspection scope:** Read-only review of the repository at `C:\local D\FinAgent`. Secret-bearing `.env` content and SQLite document content were not read.

## How to Read This Document

- **Code present** means the inspected source contains the stated implementation.
- **Test-covered** means a repository test asserts the behavior; this inspection did not execute tests.
- **Runtime verified** requires a contemporaneous test log, browser evidence, or direct execution. No committed logs or screenshots were found, so most runtime claims remain unverified from this inspection alone.
- Student and institution details above were supplied in the documentation request, not discovered in repository source.

## 1. Repository Structure and Important Files

```text
FinAgent/
├── backend/
│   ├── app/
│   │   ├── __init__.py                 Flask factory, CORS, SQLite startup reload
│   │   ├── routes.py                   `/api` HTTP endpoints
│   │   └── services/
│   │       ├── pdf_service.py          PDF validation, PyMuPDF extraction, chunks/topics
│   │       ├── retrieval_service.py    Local lexical document retrieval
│   │       ├── llm_service.py          OpenAI-compatible and Gemini REST integrations
│   │       ├── financial_tools_service.py  Approved retrieval/calculation tools
│   │       ├── agent_service.py        Bounded agent orchestration and trace construction
│   │       └── persistence_service.py  SQLite schema and CRUD helpers
│   ├── data/finagent.sqlite3           Local SQLite database; contents not inspected
│   ├── tests/
│   │   ├── test_question_endpoint.py   RAG, persistence, summary-result tests
│   │   └── test_agent_analysis.py      Calculation and agent endpoint tests
│   ├── requirements.txt                Python dependencies
│   ├── .env.example                    Backend variable names/default examples
│   └── run.py                          Flask development entry point
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     Application-level state and page routing
│   │   ├── main.jsx                    React root bootstrap
│   │   ├── lib/api.js                  Browser-to-backend API wrappers
│   │   ├── components/                 App shell and reusable UI primitives
│   │   ├── pages/                      Dashboard, documents, research, analysis, reports, settings
│   │   └── styles.css                  Tailwind base stylesheet
│   ├── package.json                    Frontend scripts and dependencies
│   ├── package-lock.json               Resolved Node dependency tree
│   ├── tailwind.config.js              Theme configuration
│   ├── vite.config.js                  Vite React plugin configuration
│   └── .env.example                    Frontend API-base configuration example
├── README.md                           Setup and architecture document; materially outdated
├── .gitignore                          Ignore rules for secrets, SQLite, caches, builds and logs
└── FINAGENT_REPORT_CONTEXT.md          This evidence report
```

Evidence: `backend/app/routes.py`, `backend/app/services/`, `frontend/src/`, `backend/tests/`, `frontend/package.json`.

## 2. Confirmed Technology Stack

| Layer | Confirmed technology | Evidence | Status |
|---|---|---|---|
| Frontend | React 19.2.8, React DOM 19.2.8 | Installed `npm ls --depth=0` | Installed in inspected workspace |
| Frontend build | Vite 6.4.3 and `@vitejs/plugin-react` 4.7.0 | Installed `npm ls --depth=0`; `frontend/vite.config.js` | Installed/configured |
| Styling | Tailwind CSS 3.4.19, PostCSS 8.5.26, Autoprefixer 10.5.4 | Installed `npm ls --depth=0`; `frontend/tailwind.config.js` | Installed/configured |
| UI/animation | Lucide React 0.468.0; Framer Motion 11.18.2 | Installed `npm ls --depth=0`; frontend imports | Installed/configured |
| Backend | Python 3.13.1; Flask 3.1.1; Flask-Cors 6.0.1 | `python --version`; `backend/requirements.txt` | Installed/configured |
| PDF processing | PyMuPDF 1.26.3 (`fitz`) | `backend/requirements.txt`; `pdf_service.py` | Installed/configured |
| Persistence | Python standard-library `sqlite3` | `persistence_service.py` | Code present |
| HTTP LLM client | Python standard-library `urllib.request` | `llm_service.py` | Code present |

Observed tooling versions: Node `v24.14.1`, npm `11.11.0`, Python `3.13.1`.

## 3. Frontend Architecture and User Workflows

### Architecture

`frontend/src/main.jsx` mounts React in strict mode. `frontend/src/App.jsx` stores the active page, performs health/document/result loading at initialization, and passes shared state and callbacks to page components. `frontend/src/components/AppShell.jsx` supplies desktop/mobile navigation and backend-health status. `frontend/src/lib/api.js` centralizes all HTTP calls using `VITE_API_BASE_URL` or `http://localhost:5000`.

Reusable primitives: `frontend/src/components/ui/Button.jsx` and `frontend/src/components/ui/Card.jsx`. The current Tailwind theme in `frontend/tailwind.config.js` uses a light financial dashboard palette with a green primary color.

### Pages and Actual Workflows

| Page | Code-supported behavior | Evidence | Runtime status from this inspection |
|---|---|---|---|
| Dashboard | Loads saved documents/results, counts documents, AI summaries and agent analyses, lists recent documents and outputs | `App.jsx:loadSavedDocuments`, `App.jsx:loadSavedResults`, `DashboardPage.jsx` | Not executed in this inspection |
| Documents | PDF selection/drag-drop, upload, processing state, saved document opening, overview, page statistics, topic display, RAG question flow/source display/history, optional summary flow | `DocumentsPage.jsx`, `api.js` | Not executed in this inspection |
| Research | Selects a persisted document, submits bounded agent-analysis question, displays answer, calculations, source pages, tool trace, limitations, opens saved agent results | `ResearchPage.jsx`, `api.js:analyzeDocument` | Not executed in this inspection |
| Analysis | Shows counts and recent saved analyses, links to Research and Reports; does not generate additional analytics | `AnalysisPage.jsx` | Not executed in this inspection |
| Reports | Lists saved results, fetches one saved payload by ID, renders summaries and structured agent-analysis data | `ReportsPage.jsx`, `api.js:getSavedResult` | Not executed in this inspection |
| Settings | Shows non-secret backend status, frontend API URL, and capability statements | `SettingsPage.jsx` | Not executed in this inspection |

Every current sidebar item maps to a page ID in `App.jsx` and `AppShell.jsx`; no sidebar item is marked as planned in the inspected code.

## 4. Backend Architecture and HTTP API

### Request Handling

`backend/run.py` builds the Flask app using `create_app()` from `backend/app/__init__.py`. The app configures CORS only for `/api/*`, initializes SQLite tables, reloads persisted documents into the in-memory `DOCUMENT_STORE`, and registers `routes.api` under `/api`.

### Confirmed Endpoints

| Endpoint | Request | Success response/content | Main errors | Evidence |
|---|---|---|---|---|
| `GET /api/health` | None | `{status: "ok", service: "FinAgent backend"}` | None defined | `routes.py:health` |
| `GET /api/documents` | None | `{success, documents[]}` with document metadata | `500` persistence failure | `routes.py:saved_documents`, `persistence_service.py:list_documents` |
| `POST /api/upload` | `multipart/form-data`, field `file` | Structured PDF/document intelligence response | `400`, `413`, `422` from `PDFProcessingError` | `routes.py:upload_pdf`, `pdf_service.py:process_pdf_upload` |
| `POST /api/documents/<id>/summary` | None | AI summary plus provider/model/disclaimer; saves successful result | `404`, provider error; `503` if unconfigured | `routes.py:summarize_document`, `llm_service.py:generate_document_summary` |
| `GET /api/documents/<id>/questions` | None | `{success, document_id, questions[]}` | `404`, `500` | `routes.py:document_question_history` |
| `POST /api/documents/<id>/question` | JSON `{question}` | Grounded answer, `source_pages`, source excerpts/scores/matched terms, provider/model and disclaimer when LLM is available | `400` empty/long/weak query; `404`; `422` no chunks; `503` no LLM | `routes.py:answer_document_question` |
| `POST /api/documents/<id>/analyze` | JSON `{question}` | Structured agent-analysis payload including answer, findings, calculations, sources, trace and limitations | `400` invalid question; `404`; LLM/provider error; `503` unconfigured | `routes.py:analyze_document`, `agent_service.py:analyze_document_with_agent` |
| `GET /api/results` | None | `{success, results[]}` metadata | `500` | `routes.py:saved_results` |
| `GET /api/results/<result_id>` | None | `{success, result}` with persisted payload | `404`, `500` | `routes.py:saved_result`, `persistence_service.py:get_result` |

All API error messages are generated by application code. The API does not return LLM keys. The server is configured with Flask debug mode in `backend/run.py`; this is suitable for local development but not a production deployment configuration.

## 5. PDF Processing and Document Storage

### Upload and Extraction

`pdf_service.py:process_pdf_upload` accepts `.pdf` filenames with allowed MIME types `application/pdf` or `application/x-pdf` (an empty MIME type is accepted), sanitizes the filename using `secure_filename`, and enforces a 25 MiB streamed upload limit. `_copy_to_temp` writes to a `NamedTemporaryFile`; the temporary file is removed in a `finally` block after PyMuPDF opens it.

For each PDF page, PyMuPDF `page.get_text()` supplies extracted text. The response contains a UUID document ID, page count, character count, word count, average words per page, pages with text, low-text pages (under 25 words), preview, optional metadata title, PDF metadata, page statistics, and deterministic financial-topic counts.

### Topic Detection and Chunking

`_detect_financial_topics` counts exact, case-insensitive occurrences of 17 terms: revenue, net income, profit, loss, assets, liabilities, equity, cash flow, operating income, expenses, debt, earnings, margin, risk, investment, stock, and shareholder. These are keyword frequencies, not a financial-importance model.

`_build_page_chunks` makes page-aware chunks of up to 180 whitespace-separated words with a 40-word overlap. Each chunk retains a `chunk_id`, original PDF `page`, text and word count. This is the evidence basis for page citations.

### Storage Behavior

Contrary to the stale README, uploaded PDF binaries are not retained, but extracted text, per-page text, chunks, metadata and document response data are stored in SQLite. At startup, `create_app()` calls `load_documents()` and restores them into `DOCUMENT_STORE`, enabling retrieval after server restart. Evidence: `pdf_service.py`, `persistence_service.py:save_document`, `persistence_service.py:load_documents`, `app/__init__.py:create_app`.

## 6. Actual RAG Status

### Present

- Page-aware chunk creation: `pdf_service.py:_build_page_chunks`.
- Retrieval from the selected document only: `retrieval_service.py:retrieve_relevant_chunks` receives that document's chunks.
- Local lexical scoring: tokens are lowercased, stop words removed, and chunk scores use term frequency multiplied by an IDF-like factor. Results are sorted by score, page and chunk ID.
- Source evidence: each retrieved result includes `chunk_id`, page, full chunk text, excerpt, score and matched terms. Question and agent responses expose `source_pages`.
- LLM grounding prompts: `_build_agent_final_prompt` instructs the model to use only retrieved passages and verified calculations.

### Not Present

- No embeddings model.
- No vector database, ChromaDB, FAISS, Pinecone or semantic-vector retrieval.
- No LangChain retrieval chain.

Repository-wide search found no source/dependency use of these technologies. README text contains obsolete negative references only.

### Critical Current Defect

`backend/app/services/llm_service.py:_build_question_prompt` at lines 48–55 constructs `passages` but has no return statement. The intended question prompt return block appears after an unconditional `raise` in `_generate_text` at lines 274–284, making it unreachable. Therefore, code inspection indicates `generate_grounded_answer()` may call the configured question provider with a missing/`None` question prompt. Existing question-endpoint tests mock `generate_grounded_answer`, so they do not exercise this live-provider path. This is **code-detected, unexecuted**, but should be investigated before claiming live RAG Q&A is reliable.

## 7. LLM Provider and Configuration

`llm_service.py:get_llm_config` reads these backend environment variable names:

| Variable | Purpose | Default/Example available in repository |
|---|---|---|
| `LLM_PROVIDER` | Provider selector | Default code value `openai`; example value `openai` |
| `LLM_MODEL` | Model name | Default code value `gpt-4o-mini`; example value `gpt-4o-mini` |
| `LLM_API_KEY` | Backend-only credential | Empty in `.env.example`; actual value not inspected |
| `LLM_API_BASE_URL` | Optional OpenAI-compatible base URL | Empty in `.env.example` |
| `CORS_ORIGINS` | Comma-separated frontend origins | Local Vite defaults in `.env.example` |
| `FINAGENT_DB_PATH` | Optional SQLite path override | Empty in `.env.example` |
| `VITE_API_BASE_URL` | Browser API base URL | `http://localhost:5000` in frontend example |

The source supports `openai`, `openai-compatible`, and `gemini` provider values. OpenAI-compatible requests target `/chat/completions`; Gemini requests target Google Generative Language `generateContent`. Summary, question-answering, tool-plan, and final-analysis calls use backend-side `urllib` requests and provider/model labels are returned in successful responses.

**Provider/model currently configured:** unverified. The protected `backend/.env` was intentionally not read. The repository source does not itself prove that Gemini, any other provider, or a particular model is active at runtime.

## 8. Financial Tools and Bounded Agent

### Approved Toolset

`financial_tools_service.py:REGISTERED_TOOLS` registers exactly three tools:

| Tool | Inputs and validation | Output/formula | Evidence |
|---|---|---|---|
| `search_document` | Non-empty query; limit clamped to 1–8 | Local retrieval sources and source pages | `search_document` |
| `calculate_revenue_growth` | Numeric prior/current revenue; rejects boolean/missing/non-numeric input and prior revenue of zero | `((current - prior) / prior) * 100`, rounded to 2 decimals | `calculate_revenue_growth` |
| `calculate_profit_margin` | Numeric profit/revenue; rejects boolean/missing/non-numeric input and zero revenue | `(profit / revenue) * 100`, rounded to 2 decimals | `calculate_profit_margin` |

The calculation functions accept labels and an evidence string. The formulas are arithmetic operations only; the service does not independently parse numeric values from PDF prose. Numeric tool inputs are selected by the LLM tool plan, which is instructed to use only explicitly present source/user values.

### Agent Workflow

`agent_service.py:analyze_document_with_agent` performs the following bounded flow:

1. Validates a non-empty question of at most 1,200 characters.
2. Executes one grounding `search_document` call (limit 6).
3. Returns an `insufficient_evidence` state without LLM planning if no sources were retrieved.
4. Calls `generate_analysis_tool_plan`, which requests JSON for only revenue-growth and profit-margin calculations.
5. Ignores malformed, unapproved, and additional `search_document` plan calls. It permits at most `MAX_TOOL_CALLS - 1` calculation calls after grounding search; `MAX_TOOL_CALLS` is 4.
6. Executes registered functions only through `execute_financial_tool`; it does not execute generated Python, shell commands, or arbitrary tool names.
7. Calls `generate_agent_final_answer` with retrieved sources, executed calculation outputs and tool trace.
8. Returns and persists actual `tools_executed`, calculations, findings, source pages, limitations, provider/model and disclaimer.

The agent is custom Python orchestration, not a general autonomous agent framework.

## 9. LangChain and LangGraph Status

No LangChain or LangGraph package is listed in `backend/requirements.txt` or `frontend/package.json`, and no source import/reference was found in repository search. There are no graphs, nodes, LangChain tools, chains, memory objects, or LangGraph state transitions.

The implemented workflow is a bespoke bounded sequence in `backend/app/services/agent_service.py`. It performs one mandatory retrieval, optional validated calculation calls, and one final LLM call. Claims that the project uses LangChain or LangGraph would be inaccurate based on the inspected repository.

## 10. Database and Persistence

`persistence_service.py:init_database` creates the following local SQLite tables in `backend/data/finagent.sqlite3` unless overridden by `FINAGENT_DB_PATH`:

| Table | Stored data | Evidence |
|---|---|---|
| `documents` | ID, filename, timestamp, metadata JSON, extraction response JSON, full extracted text, page-text JSON and chunk JSON | `init_database`, `save_document` |
| `question_history` | Document ID, question, answer, status, source pages/sources JSON, provider/model/disclaimer and timestamp | `save_question_history`, `list_question_history` |
| `saved_results` | Document ID, result type, title, status, payload JSON and timestamp | `save_result`, `list_results`, `get_result` |

Parameterized SQLite queries are used for values. Two indexes support document-specific question history and saved-results lookup. No database migration system, user accounts, access control, encryption-at-rest, backup strategy, or retention/deletion endpoint is implemented.

The database file was present during inspection, but its content, document text and stored results were not read for privacy reasons.

## 11. Security, Privacy and Configuration Observations

### Implemented Safeguards

- API credential is only read by backend code; frontend code exposes only `VITE_API_BASE_URL`. Evidence: `llm_service.py:get_llm_config`, `frontend/src/lib/api.js`.
- `.env`, backend `.env`, frontend `.env`, SQLite database files, Node modules, build output and `*.log` files are ignored by `.gitignore`.
- PDF filenames are sanitized with Werkzeug `secure_filename`.
- The upload is size-limited to 25 MiB and temporary PDF material is removed after extraction.
- LLM prompts explicitly prohibit unsupported financial facts and investment advice.
- Agent tool execution is allowlisted and bounded.

### Risks and Limitations

- Extracted full document text, chunks, question answers and result payloads persist unencrypted in local SQLite. This may contain sensitive financial information.
- CORS defaults are local Vite origins only, but Flask runs with `debug=True` in `backend/run.py`; not suitable for a production deployment.
- MIME validation permits an empty MIME type and relies on filename extension plus PyMuPDF parse failure; it is not a content-signature check.
- LLM API calls send excerpts or document text to the selected external provider when configured. No consent/audit/retention controls for provider transmission are implemented.
- No authentication, authorization, rate limiting, CSRF strategy, upload-virus scanning, encryption, or secure secret manager is present.
- The `print` diagnostics in some OpenAI-compatible error paths can include upstream error bodies; such bodies may disclose provider response details in server logs.
- No log files or screenshot files were found in the repository at inspection time.

## 12. Setup and Execution Instructions From Repository Evidence

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The entry point binds Flask to `0.0.0.0:5000` with debug mode enabled. Evidence: `README.md`, `backend/run.py`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Available scripts in `frontend/package.json` are `dev`, `build`, and `preview`. The Vite dev script binds to `0.0.0.0`. The frontend uses `VITE_API_BASE_URL` or defaults to `http://localhost:5000`.

### Tests

```powershell
cd backend
python -B -m unittest discover -s tests

cd ..\frontend
npm run build
```

These commands are supported by repository structure and scripts. They were **not run during this read-only inspection**.

## 13. Tests, Logs, Screenshots and Evidence of Working Features

### Tests Present

`backend/tests/test_question_endpoint.py` contains seven test methods covering:

- Grounded question response/source presence, using a mocked LLM answer.
- Insufficient evidence without invoking LLM answer generation.
- Question validation and unknown-document response.
- Document reload into `DOCUMENT_STORE` after app recreation.
- Saved-document and persisted-question-history endpoints.
- Summary result persistence and retrieval, using a mocked summary generator.

`backend/tests/test_agent_analysis.py` contains nine test methods covering:

- Revenue growth and profit-margin arithmetic.
- Division-by-zero validation for both formulas.
- Agent endpoint response/persistence, with mocked plan and final LLM output.
- Empty question validation.
- Insufficient-evidence response without LLM plan call.
- Rejection/limitation handling for unapproved and excess plan tool calls.
- `503` behavior for unconfigured LLM planning.

The source contains 16 test methods in total. Test source demonstrates intended and mocked behavior; it does not prove a live Gemini call, browser interaction, or test success in this inspection.

### Logs and Build Artifacts

- No `.log` files were found by recursive repository inspection.
- `frontend/dist` exists with an `index.html`, CSS and JavaScript bundle, dated 14 October 2026. A dist directory alone does not prove the current source built successfully.
- No screenshots, videos, test-result XML/JSON, coverage reports, or committed API capture artifacts were found.

## 14. Feature Status Matrix

| Feature | Status | Evidence/qualification |
|---|---|---|
| React financial dashboard UI | Complete in source | `frontend/src/`; browser behavior unverified in this inspection |
| Flask health and API routes | Complete in source | `routes.py`; endpoint runtime unverified |
| PDF validation/PyMuPDF extraction/page analysis | Complete in source; partially test-supported through PDF uploads in test fixtures | `pdf_service.py`; tests upload generated PDFs |
| Deterministic topic detection | Complete in source | `pdf_service.py:_detect_financial_topics`; no direct dedicated test |
| SQLite document and result persistence | Complete in source; test-supported | `persistence_service.py`; persistence tests |
| RAG-like page-aware lexical retrieval | Present in source; test-supported at route level with mocked LLM | `retrieval_service.py`; `test_question_endpoint.py` |
| Live RAG LLM answer reliability | Partial/at risk | `_build_question_prompt` missing return; direct live LLM test absent |
| Optional LLM summary | Complete in source; mock-tested | `llm_service.py`, `test_summary_result_is_saved_and_retrievable` |
| Gemini provider support | Complete in source | `llm_service.py:_gemini_*`; active configuration/live call unverified |
| Bounded agent orchestration | Complete in source; mock-tested | `agent_service.py`, `test_agent_analysis.py` |
| Revenue growth/profit margin | Complete in source and unit tested | `financial_tools_service.py`, `FinancialToolsTest` |
| Other financial ratios/comparisons | Absent | Only two arithmetic calculation tools are registered |
| Reports/result reopening | Complete in source | `ReportsPage.jsx`, results endpoints; browser behavior unverified |
| LangChain/LangGraph | Absent | No dependency/import/source reference |
| Embeddings/vector database/semantic search | Absent | Local lexical retrieval only |
| OCR/scanned-PDF extraction | Absent | PyMuPDF text extraction only; zero words raises error |
| Authentication/roles/multi-user tenancy | Absent | No related source/dependency/endpoints |
| External financial-data API | Absent | No related source/dependency/endpoints |
| Formal generated report export (PDF/DOCX) | Absent | Reports page is a saved-result viewer only |

## 15. Known Errors, Limitations and Documentation Gaps

1. **High priority:** `llm_service.py:_build_question_prompt` has no return statement; the intended prompt text is unreachable after a `raise` in `_generate_text`. Live RAG Q&A should be retested and repaired before being presented as reliable.
2. **README is obsolete:** `README.md` states that RAG, persistence, agents and Gemini-related functionality are not implemented, while current code implements local lexical retrieval, SQLite persistence and a bounded custom agent. It also describes documents as memory-only. Do not use the README as the current technical truth until updated.
3. **No direct test for live LLM providers:** all test cases that reach LLM operations use `unittest.mock`; there is no reproducible live Gemini/OpenAI-compatible integration test.
4. **No frontend automated tests:** no React test framework, component tests, browser automation, screenshots or accessibility test artifacts were found.
5. **No observability artifacts:** no repository logs, error tracking configuration, performance measurements, coverage reports, screenshots or test-run outputs were found.
6. **Persistence is local and unencrypted:** local SQLite stores extracted text and analysis data; no retention controls or delete UI/API is available.
7. **Agent is bounded but not independently evidence-validating numeric extraction:** tool-plan numeric inputs are LLM-selected. Prompts and source excerpts constrain behavior, but there is no deterministic parser that cross-checks every planned number against its cited passage.
8. **Development server configuration:** Flask debug mode and no authentication are appropriate for a college/local prototype, not a deployed public service.

## 16. Project Objective-to-Evidence Mapping

| Proposed objective | Relevant implementation evidence | Academic claim supported now |
|---|---|---|
| Upload and analyze financial PDFs | `pdf_service.py:process_pdf_upload`; `routes.py:upload_pdf`; `DocumentsPage.jsx` | Code supports PDF intake, text extraction, page metrics and topic counts |
| Provide document-grounded Q&A with citations | `pdf_service.py:_build_page_chunks`; `retrieval_service.py:retrieve_relevant_chunks`; `routes.py:answer_document_question` | Code supports local lexical retrieval and page references; live LLM Q&A is currently at risk due to prompt helper defect |
| Persist prior work | `persistence_service.py`; `app/__init__.py:create_app`; document/question/result endpoints | Code and tests support SQLite persistence/reload |
| Generate AI summaries | `llm_service.py:generate_document_summary`; `routes.py:summarize_document`; `DocumentsPage.jsx` | Optional backend-only summary exists; live provider requires configuration and independent proof |
| Perform agentic financial analysis | `agent_service.py:analyze_document_with_agent`; `financial_tools_service.py`; `routes.py:analyze_document` | Bounded, allowlisted tool-planning and execution workflow exists |
| Calculate revenue growth and profit margin | `financial_tools_service.py:calculate_revenue_growth`; `calculate_profit_margin`; `FinancialToolsTest` | Formulas and validation are code-present and unit-test-covered |
| Present historical outputs | `ReportsPage.jsx`; `ResearchPage.jsx`; `GET /api/results`; `GET /api/results/<id>` | Source supports saved-output listing/detail; browser behavior needs evidence |
| Use LangChain/LangGraph | No evidence; no dependency or import | Objective is not met and should not be claimed |
| Use embeddings/vector database | No evidence; retrieval is lexical | Objective is not met and should not be claimed |

## 17. Proposed Six-Chapter Academic Report Outline

### Chapter 1 — Introduction and Problem Statement

Write now: financial-PDF research problem, need for document-grounded answers, project title, student/institution details, scope and explicit non-goals. Avoid claiming autonomous web research, stock prediction, LangChain, LangGraph, embeddings or vector databases.

Needs evidence: one final dashboard screenshot and a workflow diagram based on the actual flow: PDF upload → PyMuPDF extraction/chunking → lexical retrieval → LLM (optional) → bounded calculations → SQLite result persistence.

### Chapter 2 — Literature Review and Requirement Analysis

Write now: conceptual discussion of RAG, explain that this implementation uses lexical page-aware retrieval rather than embeddings; describe bounded tool use and local persistence requirements.

Needs external academic citations: peer-reviewed/official sources on RAG, financial document processing, LLM limitations, retrieval evaluation and privacy. Do not cite repository code as academic literature.

### Chapter 3 — System Design and Methodology

Write now: frontend/backend architecture, Flask routes, React pages, service boundaries, database schema, CORS design, local SQLite persistence, approved agent-tool list and formulas.

Needs artifacts: architecture diagram, ER/table diagram, sequence diagram for question answering and agent analysis. Use exact service names and endpoint contracts documented above.

### Chapter 4 — Implementation

Write now: technology stack/version table, PDF extraction rules, 180-word/40-word-overlap chunks, lexical scoring, LLM configuration names, prompt constraints, agent call cap, formulas and validation. Cite source paths/functions.

Needs screenshots: Documents upload/result page, source-excerpt expansion, Research agent output with tool trace and calculations, Reports saved-result detail, Settings non-secret status.

### Chapter 5 — Testing, Results and Discussion

Write now: table of existing tests and their intent, clearly marking mocks versus live provider coverage; known limitations and risk analysis.

Needs execution evidence: fresh backend test console output, frontend build console output, a valid financial-PDF upload response, valid/insufficient-evidence RAG API response, live configured summary response, live agent analysis with calculation, restart/persistence evidence, and browser screenshots. Do not report pass rates, response times, accuracy, or live Gemini behavior until measured and captured.

### Chapter 6 — Conclusion and Future Work

Write now: implemented prototype conclusion and honest scope limitations. Future work can include repair/testing of live RAG prompt path, deterministic numeric evidence validation, embeddings/vector retrieval, authentication, encrypted storage, OCR, report export, observability, evaluation and deployment hardening.

## Final Evidence Checklist for the Academic Report

- [ ] Run `python -B -m unittest discover -s tests` from `backend`; capture the full passing output and date.
- [ ] Run `npm run build` from `frontend`; capture successful output and date.
- [ ] Repair and retest the `_build_question_prompt` defect before taking live RAG screenshots or claiming live RAG reliability.
- [ ] Capture `GET /api/health` response.
- [ ] Upload a real, non-sensitive financial PDF; capture document overview, topics and page analysis.
- [ ] Submit one grounded RAG question; capture answer, source page badges and source excerpt. Also capture an insufficient-evidence case.
- [ ] With a configured provider, capture a real summary response while masking document-sensitive content as needed.
- [ ] Run an agent analysis whose PDF explicitly states two revenue periods and profit/revenue values; capture tool trace, formulas, source pages, limitations and saved result.
- [ ] Restart Flask and show the same document can be selected/retrieved afterward; capture document/result persistence.
- [ ] Capture Reports result selection/detail and Settings non-secret status.
- [ ] Record hardware, operating system, Python/Node versions, test command outputs, input-document source/permissions and any measured response times in a reproducibility appendix.

