# AGENTS.md — cooking-agent-service

## Project Purpose

Lightweight Agent service that serves as the decision‑making core for a cooking‑recommendation system. It is invoked by the upper‑layer business module (`cooking-web-service`), executes a LangGraph‑orchestrated LLM Agent workflow, and returns recommendation results.

This project does **not** handle UI or persistent business data — those are responsibilities of `cooking-web-service`.

---

## Tech Stack

- Python, virtualenv (`.venv` at project root)
- LangGraph, LangChain, FastAPI, Pydantic / pydantic‑settings (used by `common/` config)

---

## Project Structure

```
cooking-agent-service/
├── agent/                      # Agent core (LangGraph orchestration)
│   ├── graph/                  # Graph construction
│   │   ├── graph.py            # Build & compile LangGraph
│   │   ├── nodes.py            # Node logic
│   │   ├── state.py            # State definition
│   │   └── llm.py              # LLM init & config (single source)
│   ├── prompts/                # Prompt templates
│   │   ├── system-*.md
│   │   ├── human-*.md
│   │   ├── ai-*.md
│   │   └── utils.py            # Loading utilities
│   ├── services/               # Agent execution services
│   └── tools/                  # Agent tools
├── app/                        # External API layer
│   ├── api/routes/             # FastAPI routes (request/response only)
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Service layer (e.g., HTTP clients)
│   ├── core/                   # Placeholder (do not use for Agent logic)
│   └── main.py                 # App entry (create app, register routes, middleware)
├── common/                     # Shared cross‑service utilities
│   ├── config.py               # All configuration (Settings)
│   └── logging.py              # Logging infrastructure
├── tests/                      # Unit tests
├── scripts/                    # Project‑level scripts
├── main.py                     # Project entry (if any)
├── requirements.txt
├── .env.example
└── ...
```

---

## Commands

Run all commands from project root with the virtualenv (`.venv`) activated.

- **Dev**: `python -m app.main` (uses `uvicorn.run` programmatically, reading host/port/reload from config; use `/scripts/start-agent.sh` eventually)
- **Format**: `ruff format agent/ app/ common/ tests/` (check only: `ruff format --check agent/ app/ common/ tests/`)
- **Lint**: `ruff check agent/ app/ common/ tests/`
- **Test**: `pytest` (with coverage: `pytest --cov=app`)

---

## External Reference Docs

**Do not read all documents at once** – only access when needed.

- **@design-agreement**: Critical constraint documents. Read relevant content before coding and retain key points.
- **@web-service**: The business module (frontend + backend API). This Agent service **calls back** its recipe query/detail APIs. Follow the pagination conventions and interface contracts in `design/agreement/api-conventions.md`. Read‑only reference – never modify its code.
- **@requirements**: Project requirements. Read `99-summary.md` first for overview.
- **@sprints**: Iteration plans. Generally not needed; refer to `@design-agreement` instead. Use only when you need the original plan.

---

## Boundary Constraints

This project is the **decision core**; it is responsible **only** for:

- Receiving decision context via HTTP API from the business module.
- Executing the Agent workflow: knowledge matching, direction recommendation, candidate filtering/confirmation, final ranking.
- Fetching recipe/decision data from `cooking-web-service` via HTTP.
- Returning the final decision result.

**Forbidden**:

- Any frontend rendering logic.
- Direct management of business data (users, preferences, recipe master data, weights, usage logs, etc.) — these are maintained by `cooking-web-service`.
- Modifying code outside `cooking-agent-service` (unless explicitly allowed).
- Custom decision behaviours beyond the contract defined for the business module.

---

## Coding Constraints

### Agent Core (`agent/`)

- This directory holds **only** the decision logic – no HTTP layer.
- Graph definition → `agent/graph/graph.py`; nodes → `agent/graph/nodes.py`; state → `agent/graph/state.py`. Do not build graphs or modify state inside node functions.
- LLM instances must come from `agent/graph/llm.py` – never create directly or hardcode endpoints.
- All prompts must be stored in `agent/prompts/` and loaded via `agent/prompts/utils.py` – no hardcoded prompts.
- `agent/services/` holds the actual execution entry points for the Agent workflow.

### API Service Layer (`app/`)

- Routes go in `app/api/routes/` – they handle request/response and call services. No business logic in route handlers.
- `app/core/` is a placeholder – all config goes to `common/config.py`; shared infra goes to `common/`. Do not implement Agent functionality here.
- `app/main.py` – only app creation, route registration, middleware – no business logic.
- HTTP clients that call back to `cooking-web-service` live in `app/services/` – strictly follow the interface contracts and pagination conventions from `@web-service`/`design/agreement/api-conventions.md`. No improvisation.

### Testing (TDD)

- Write tests **before** implementation. Each spec must include ≥3 cases: happy path, edge/boundary, invalid input. No single‑value assertions.
- Implement generically – never hardcode values to pass tests.
- On test failure: fix the logic – never modify, delete, or loosen the test. If the test itself is wrong, explain before editing.

### Comments

- All comments in **Chinese**.
- Use Google‑style docstrings (Args/Returns/Raises) for public functions/classes. Module‑level docstring required for every module.
- Line comments explain **why**, not what the code does.
- Private functions (leading `_`) need not have docstrings.

### Logging

- Use `common/logging.py`'s `get_logger(__name__)` – no `print` or custom loggers.
- Log critical events:
  - App startup/shutdown.
  - Agent decisions (request/response/duration/errors) in `agent/services/`.
  - Calls to web‑service APIs (requests & errors) in `app/services/`.
- Route handlers should log only at debug level to avoid noise.

### Environment Variables

- All config is in `common/config.py` under the `Settings` class, accessed via `get_settings()`.
- Use environment variables only for deployment‑sensitive or environment‑dependent values – add them as `Settings` fields.
- Never read `os.environ` directly in application code.
- Secrets (API keys, tokens) must come from `Settings`/`.env`. Use `.env.example` as a template.

### Project‑wide Rules

- Project‑level scripts go in `/scripts/` – only those are allowed there.
- Follow the folder structure. If new folders are needed, ask first.
- New dependencies/libraries – ask before adding.
- API implementation must follow contracts from `@web-service` – no improvisation.
- When modifying code, review and update comments if they no longer match the logic.
- After coding: **format** first, then **lint**. Fix all linting errors until they pass.
  - `ruff format agent/ app/ common/ tests/` → `ruff check agent/ app/ common/ tests/`
- If the changes involve business logic or API, also run `pytest` after linting and ensure all tests pass before marking the task complete.