# FinAgent

FinAgent is a financial research and analysis assistant. The project is being built incrementally; the current milestone is Phase 1, focused on document intelligence for uploaded financial PDFs.

This repository does not yet implement RAG, embeddings, ChromaDB, LangChain, LangGraph, autonomous agents, portfolio advice, stock prediction, or external financial-data workflows.

## Phase Status

- Phase 0 - Foundation: COMPLETE
- Phase 1 - Document Intelligence: CURRENT
- Phase 2 - RAG: PLANNED
- Phase 3 - Financial Tools: PLANNED
- Phase 4 - Agentic AI: PLANNED
- Phase 5 - External Financial Data: PLANNED
- Phase 6 - Visualization & Reports: PLANNED
- Phase 7 - Evaluation & Deployment: PLANNED

## What Phase 0 Implemented

- React + Vite frontend
- Flask backend
- PyMuPDF PDF extraction
- `GET /api/health`
- `POST /api/upload`
- Real frontend-to-backend PDF upload
- JSON response with filename, page count, and extracted character count

## What Phase 1 Implements

- Structured document ID for each processed upload
- Page count, character count, word count, and average words per page
- Text coverage and low-text page detection
- Per-page word and character statistics
- First meaningful document preview
- PDF metadata extraction when available
- Deterministic local financial topic detection
- Optional backend-only AI summary endpoint
- Improved document intelligence UI with overview, topics, page analysis, and summary state
- Backend health status indicator in the frontend shell

## Tech Stack

- Frontend: React, Vite, Tailwind CSS, Lucide React, Framer Motion
- Backend: Python, Flask, Flask-CORS, PyMuPDF
- Optional LLM: OpenAI-compatible chat-completions API through backend environment variables

## Project Structure

```text
finagent/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   └── pdf_service.py
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── .env.example
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── .env.example
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── .gitignore
└── README.md
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The backend runs at `http://localhost:5000`.

Copy `backend/.env.example` to `backend/.env` if you need local overrides. Do not commit real secrets.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

Copy `frontend/.env.example` to `frontend/.env` only for local frontend settings such as `VITE_API_BASE_URL`.

## Environment Variables

Backend:

```env
FLASK_APP=run.py
FLASK_DEBUG=1
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=
LLM_API_BASE_URL=
```

Frontend:

```env
VITE_API_BASE_URL=http://localhost:5000
```

The LLM API key is backend-only. Never place an LLM key in React code or a frontend environment variable.

## API Endpoints

### `GET /api/health`

Returns:

```json
{
  "status": "ok",
  "service": "FinAgent backend"
}
```

### `POST /api/upload`

Accepts a PDF file in `multipart/form-data` under the `file` field.

Returns a structured document intelligence response:

```json
{
  "success": true,
  "document_id": "uuid",
  "filename": "annual-report.pdf",
  "pages": 20,
  "characters": 63404,
  "characters_extracted": 63404,
  "words": 10500,
  "average_words_per_page": 525,
  "text_pages": 20,
  "low_text_pages": [],
  "preview": "First meaningful text...",
  "document_title": "Annual Report",
  "metadata": {},
  "page_statistics": [],
  "financial_topics": [],
  "status": "processed"
}
```

### `POST /api/documents/<document_id>/summary`

Generates an optional AI summary for a previously processed document.

- If `LLM_API_KEY` is configured, the backend calls the configured OpenAI-compatible provider.
- If no key is configured, the endpoint returns a clear unavailable state and the application continues working.
- The frontend never receives or stores the API key.

## Current Limitations

- Processed document text is stored only in backend memory for the current server process.
- PDF files are not stored permanently.
- AI summary is optional and unavailable unless backend LLM variables are configured.
- Financial topics are deterministic keyword counts, not financial importance scores.
- No RAG, semantic search, embeddings, vector database, agents, stock prediction, recommendations, or financial advice are implemented.

## Development Notes

- `.env`, `backend/.env`, `frontend/.env`, `node_modules`, `dist`, Python caches, and virtual environments are ignored.
- Keep API keys out of source control.
- Phase 1 intentionally stops at document intelligence and optional summarization.
