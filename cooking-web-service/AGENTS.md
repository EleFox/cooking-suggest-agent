# cooking-web-service

## Project Purpose

Lightweight mobile H5 app for cooking decision assistance. This service provides the frontend UI and backend API, which forwards user conditions to an external Agent Service (not part of this repo) and displays results.

## Tech Stack

### Frontend

- React 19, TypeScript, Vite, Node.js ≥24, pnpm 10
- Tailwind CSS 4, shadcn/ui, Radix UI, Lucide React
- React Router, React Hook Form + Zod + @hookform/resolvers
- Zustand, Framer Motion

### Backend

- Python 3.x, virtualenv at `backend\.venv`
- FastAPI

## Project Structure

```
cooking-web-service/
├── frontend/
│   ├── src/
│   │   ├── api/          → Backend API request functions
│   │   ├── components/   → Reusable UI components
│   │   ├── pages/        → Page-level components
│   │   ├── router/       → Route config
│   │   ├── stores/       → Zustand stores
│   │   ├── hooks/        → Custom React hooks
│   │   ├── schemas/      → Zod validation schemas
│   │   ├── types/        → TypeScript types
│   │   ├── lib/          → Utilities
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/routes/   → FastAPI route handlers
│   │   ├── schemas/      → Pydantic models (req/res)
│   │   ├── services/     → Business logic & Agent client
│   │   ├── core/         → Config & shared infra
│   │   ├── main.py       → App entry (router registration, middleware)
│   │   └── __init__.py
│   ├── tests/
│   ├── requirements.txt
│   └── ...
├── docs/
│   └── ...               → For documents
├── scripts/              → Service start scripts
└── ...
```

## Commands

### Frontend (`/frontend`)

- Dev: `npm run dev` or `../scripts/start-frontend.sh`
- Build: `npm run build`
- Format: `npm run format` (check only: `npm run format:check`)
- Lint: `npm run lint`

### Backend (`/backend`, activate venv)

- Dev: `../scripts/start-backend.sh`
- Format: `ruff format app/ tests/` (check: `ruff format --check app/ tests/`)
- Lint: `ruff check app/ tests/`
- Test: `pytest` (with coverage: `pytest --cov=app`)

### Project

- Start all dev services: `/scripts/start.sh`

## External Reference Documents

The following references point to project documentation stored in separate directories. **Do not read all documents at once** – only access them when needed, following the guidance below.

- **@agent-docs**: Contains the project documentation for the system's core agent service. When you need to interface with the agent service, you should refer to the documentation in this reference. Unless I explicitly allow it, you must not examine any content outside the documentation to understand the agent service's business logic.

- **@design-docs**: Contains the most critical project design documents and various constraint specifications. **Before starting any code development**, you must read the relevant content as directed in these documents and remember the key points.

- **@ui-docs**: Contains UI prototypes (wireframes) created in Penpot – these are **not** production‑ready mockups. Use these documents to understand the page structure and interactions, then implement the actual pages according to the specific requirements. These designs serve as a baseline reference; implementation should ultimately follow the provided requirements.

- **@requirements**: Contains the project's requirement analysis. Before reading any files in this folder, first read `99-summary.md` to get an overview of the project and guidance on how to use the other files.

- **@sprints**: Contains the project's iteration plans. Generally, you do not need to consult this folder; the relevant documents in `@design-docs` should suffice. Only refer to this when you need to understand the original iteration plan.

---

## Boundary Constraints

### Frontend

**Only** responsible for:

- Rendering UI, user input, calling backend API, displaying results.

**Forbidden**:

- Agent logic, direct LLM calls, knowledge base access, business rule storage.

### Backend

**Only** responsible for:

- HTTP API, request validation, orchestration, communication with Agent Service, returning data.

**Forbidden**:

- Direct LLM calls, implementing Agent functionality.

---

## Coding Constraints

### Frontend

- All backend requests must be defined in `src/api/` and imported.
- Prefer `shadcn/ui` components; implement custom only if missing.
- Use Tailwind CSS only – no raw CSS or other UI libraries.
- Global state: Zustand only; local component state: `useState`.
- Complex forms: React Hook Form + Zod – no manual form state/validation.

### Backend

- Routes in `backend/app/api/routes/` – only request/response handling, call services. No business logic in routes.
- `core/` for config/infra only – no Agent code.
- `main.py` – only app creation, router registration, middleware – no business logic.
- **TDD strictly**:
  - Write tests before implementation – each spec must include ≥3 cases (happy, edge, invalid). No single‑value assertions.
  - Implement generically – never hardcode to pass specific tests.
  - On test failure: fix logic, never modify/relax/delete the test. If test is wrong, explain before editing.

### Comments

- All comments in Chinese; use Google‑style docstrings (Args/Returns/Raises) plus concise line comments that explain "why", not repeat the code.
- Backend: only modules and public interfaces – module docstring on every file; Google‑style docstring on public functions/classes; line comments on constants and complex logic. Private (`_`‑prefixed) functions need no docstring.
- Frontend: only public methods/functions, exported components, and global constants/variables get comments.

### Logging

- Obtain loggers via `get_logger(__name__)` from `app/core/logging.py` – no `print` or ad‑hoc loggers.
- Log key events: app startup/shutdown; Agent calls (request/response/duration/errors) in `services/`.
- Keep route‑level logs at debug level to avoid access‑log noise.

### Environment Variables

- All environment‑driven configuration (ports, URLs, flags, secrets, etc.) must be declared in `app/core/config.py` (`Settings`) and accessed via `get_settings()`.
- Reference environment variables only when a value varies by environment or is deployment‑specific; never hardcode such values in modules.
- Never read `os.environ` directly in application code; add the field to `Settings` instead.
- Secrets (API keys, tokens etc.) , env config etc must come from `Settings`/`.env`; use `.env.example` as the template.

### Project‑wide

- All project‑level scripts must be placed in `/scripts/`.
- Follow folder structure; if new folders needed, ask first.
- New dependencies/libraries – ask before adding.
- Follow API specs from `docs/apis/` – no improvisation.
- When changing code, check that existing comments still match the new logic; if not, update them in the same change.
- After coding:
  - Run formatting, then linting. Fix all errors until pass.
  - Backend: after lint pass, run `pytest` to ensure tests pass (if logic/API changed).
- Finish only when all checks (format, lint, test) succeed.
