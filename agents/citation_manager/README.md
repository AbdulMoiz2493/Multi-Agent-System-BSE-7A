## Citation Manager Agent
The Citation Manager Agent provides citation parsing, formatting, and long‑term memory (LTM) storage. It is consumed via the Supervisor and should not be called directly from the UI in development.

### Key Endpoints
- `POST /process`: Parse free‑form text and structured metadata into a formatted citation.
  - Parameters (via `TaskEnvelope.task.parameters.agent_specific_data`):
    - `raw_text`: Free‑form text to parse.
    - `metadata`: Partial structured fields to merge.
    - `style`: Citation style (e.g., `APA`, `MLA`).
    - `source_type`: Source type (`article`, `book`, `web`).
    - `includeDOI`: Include DOI in output when present.
    - `llm_parse`: Use the LLM to assist parsing when deterministic parse is sparse.
    - `save`: Persist the citation to LTM.
    - `user_id`: Authenticated user ID for per‑user storage.
    - `save_all`: Persist even if a duplicate by DOI/title exists.

- `POST /bibliography`: Format a bibliography for a batch of items.
  - Parameters (via `TaskEnvelope.task.parameters`):
    - `items`: Array of normalized citation items.
    - `style`: Citation style (`APA` default).
    - `remove_duplicates`: Deduplicate the list by DOI/title.
    - `save`: Persist items to LTM.
    - `user_id`: Authenticated user ID.
    - `save_all`: Persist all items, bypassing duplicate checks.

- `POST /upload/pdf`: Extract references from a PDF and produce normalized citations.
  - Query params: `style`, `includeDOI`, `llm_parse`, `save`, `user_id`, `save_all`.
  - Body: `multipart/form-data` with `file`.

### Long‑Term Memory (LTM)
- Storage lives in `agents/citation_manager/ltm.py` using SQLite (`ltm_citation.db`).
- `save_to_ltm(item, style, user_id, force_save)` handles rendering and duplicate checks.
  - `force_save=True` bypasses duplicate checks for `save_all` workflows.
- `exists_duplicate(doi, title)` prevents accidental duplicates when `save_all` is false.

### Integration Notes
- All UI calls should route through the Supervisor; it enforces auth and injects `user_id`.
- The Supervisor provides `POST /api/supervisor/ltm/retrieve` for per‑user citation retrieval.

### Health & Diagnostics
- `GET /health` returns simple status.
- `GET /csl_status` reports style availability and citeproc engine status.

### Quick Commands
- Start agent:
  - `python -m uvicorn agents.citation_manager.app:app --host 127.0.0.1 --port 5016`

- Health check:
  - `curl http://127.0.0.1:5016/health`

- Process citation (local dev, call agent directly):
  - `curl -X POST http://127.0.0.1:5016/process -H "Content-Type: application/json" -d '{"message_id":"m1","sender":"CitationUI","recipient":"CitationManagerAgent","type":"task_assignment","task":{"name":"process","parameters":{"agent_specific_data":{"intent":"generate_citation","raw_text":"Raw citation text pasted by user...","metadata":{"title":"Example title","authors":["John Doe","Jane Smith"],"year":2021,"journal":"Nature","volume":"12","issue":"3","pages":"44-55","doi":"10.1234/example-doi","url":"https://example.com/article"},"style":"APA","source_type":"article","includeDOI":true,"llm_parse":true,"save":true,"save_all":true,"user_id":"user-123"}}}}'`

- Bibliography (via Supervisor):
  - `curl -X POST http://127.0.0.1:8000/api/supervisor/bibliography -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"message_id":"ui-1","sender":"CitationUI","recipient":"CitationManagerAgent","type":"task_assignment","task":{"name":"bibliography","parameters":{"items":[{"title":"T1","authors":["A"],"year":2020}],"style":"APA","remove_duplicates":true,"save":true,"save_all":true,"user_id":"user-123"}}}'`

- Upload PDF (via Supervisor):
  - `curl -X POST "http://127.0.0.1:8000/api/supervisor/upload/pdf?style=APA&includeDOI=true&llm_parse=true&save=true&user_id=user-123&save_all=true" -H "Authorization: Bearer <token>" -F "file=@C:/path/to/file.pdf;type=application/pdf"`

- LTM retrieve (via Supervisor):
  - `curl -X POST http://127.0.0.1:8000/api/supervisor/ltm/retrieve -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"agentId":"citation_manager_agent","limit":50}'`

# Supervisor: Citation Proxy Routing
This supervisor enforces authentication and proxies UI requests to the Citation Manager Agent while keeping the agent's response format intact. UI should call supervisor endpoints only.

## Endpoints
- `POST /api/supervisor/request`
  - General agent request submission. Requires `Authorization` header.
  - Body: `EnhancedRequestPayload` with `agentId`, `agent_specific_data`, etc.

- `POST /api/supervisor/upload/pdf`
  - Accepts `multipart/form-data` with a `file` field.
  - Query params: `style`, `includeDOI`, `llm_parse`, `save`, `user_id`, `save_all`.
  - Auth required. Proxies to `citation_manager_agent` `/upload/pdf` and returns its JSON unchanged.

- `POST /api/supervisor/bibliography`
  - Accepts a `TaskEnvelope` JSON as used by the citation agent.
  - Auth required. Proxies to `citation_manager_agent` `/bibliography` and returns its JSON unchanged.

## Notes
- The supervisor attaches/validates user context and forwards `save`/`save_all`/`user_id` to the agent.
- Error responses from the agent are surfaced to the UI with the same status code and a `detail` message when available.



## End-to-End Setup & Start (Backend + UI)
### Prerequisites
- Python 3.10+ and `pip`
- Node.js 18+ and `npm`
- Windows PowerShell or any terminal

### Backend Environment
- Copy the example env file and fill values if you plan to use cloud LLM mode:
  - `Multi-Agent-System-BSE-7A-Backend/.env.example` → create `Multi-Agent-System-BSE-7A-Backend/.env`
  - Keys:
    - `GEMINI_API_KEY`: required for cloud mode and intent identification.
    - `GEMINI_API_URL`: base URL for the external Gemini-like API.
  - If these are not set, `settings.yaml` with `mode: auto` falls back to mock mode.

### UI Environment
- Create `citation-manager-ui/.env` with:
  - `REACT_APP_SUPERVISOR_URL=http://127.0.0.1:8000`

### Start Order
1) Install Python deps (backend root):
   - `cd Multi-Agent-System-BSE-7A-Backend`
   - `python -m venv venv && ./venv/Scripts/Activate.ps1`
   - `pip install -r requirements.txt`

2) Start Supervisor (port 8000):
   - `python -m uvicorn supervisor.main:app --host 127.0.0.1 --port 8000 --reload`

3) Start Gemini Wrapper (port 5010):
   - In a new terminal at backend root:
   - `python -m uvicorn agents.gemini_wrapper.app:app --host 127.0.0.1 --port 5010 --reload`

4) Start Citation Manager Agent (port 5016):
   - In another terminal at backend root:
   - `python -m uvicorn agents.citation_manager.app:app --host 127.0.0.1 --port 5016 --reload`

5) Start UI:
   - `cd ../citation-manager-ui`
   - `npm install`
   - `npm start`
   - UI runs on `http://localhost:3000` and talks to Supervisor at `http://127.0.0.1:8000`.

### First Login
- Default test user:
  - Email: `test@example.com`
  - Password: `password`

### Quick Smoke Tests
- Supervisor health:
  - `curl http://127.0.0.1:8000/health`

- Login to get token:
  - `curl -X POST http://127.0.0.1:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password"}'`

- Agent health via Supervisor (requires `Authorization` header):
  - `curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/api/agent/citation_manager_agent/health`

- Single citation round-trip (Supervisor):
  - `curl -X POST http://127.0.0.1:8000/api/supervisor/request -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"agentId":"citation_manager_agent","agent_specific_data":{"intent":"generate_citation","raw_text":"Doe, J. (2021). Example Article.","style":"APA","save":true,"save_all":true}}'`

- PDF upload (Supervisor → Agent):
  - `curl -X POST "http://127.0.0.1:8000/api/supervisor/upload/pdf?style=APA&includeDOI=true&llm_parse=true&save=true&user_id=user-123&save_all=true" -H "Authorization: Bearer <token>" -F "file=@C:/path/to/file.pdf;type=application/pdf"`

### Common Pitfalls
- Token missing: Ensure UI login succeeded and `Authorization: Bearer <token>` is set.
- Ports differ: Keep Supervisor at `8000`, Citation Manager at `5016`, Gemini Wrapper at `5010` per `config/settings.yaml`.
- Cloud mode errors: Verify `GEMINI_API_KEY` and `GEMINI_API_URL` in backend `.env`.

### Instructor Checklist

- Environment prepared:
  - Backend `.env` set if using cloud mode (`GEMINI_API_KEY`, `GEMINI_API_URL`).
  - UI `.env` has `REACT_APP_SUPERVISOR_URL=http://127.0.0.1:8000`.
- Services running:
  - Supervisor on `8000`, Gemini Wrapper on `5010`, Citation Manager Agent on `5016`, UI on `3000`.
- Authentication works:
  - Login with `test@example.com` / `password`, token present in requests.
- Health and registry:
  - `GET /health` responds OK; `GET /api/agent/citation_manager_agent/health` responds OK.
- Citation flow:
  - Submit single citation via Supervisor request and receive `CompletionReport` with `formatted_citation`.
  - Upload PDF via Supervisor and receive parsed references.
- Persistence:
  - `save`/`save_all` with `user_id` results in items visible via LTM retrieve.
- Verification scripts:
  - Run `python tests/integration_test.py` from backend root.
  - Optionally run `python verify_contract.py` for API contract checks.

## Logging & Health
- Agent health:
  - `GET http://127.0.0.1:5016/health` → `{ status: "healthy", agent: "citation_manager", timestamp: "..." }`
  - `GET http://127.0.0.1:5016/csl_status` → citeproc availability and style file presence.

- Supervisor health (authenticated):
  - `GET http://127.0.0.1:8000/api/agent/citation_manager_agent/health` → `{ status: "healthy" | "degraded" | "offline" }`

