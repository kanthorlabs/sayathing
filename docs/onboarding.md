# Sayathing – Engineer Onboarding

Welcome to Sayathing, an open-source Text-to-Speech (TTS) API powered by the Kokoro engine and FastAPI. This guide helps you get productive quickly and align with project conventions.

## 1) Codebase Overview

- Top-level
	- `server/` – FastAPI app, routes, config, and exception handlers.
	- `tts/` – TTS domain: engines, engine interface, models, and voice data.
	- `docs/` – Documentation (this doc lives here).
	- `data/` – Data assets (if/when needed).
	- `pyproject.toml` – Project metadata and runtime dependencies.
	- `uv.lock` – Locked dependency graph for the `uv` package manager.
	- `docker-compose.yaml` – Local Postgres (not currently used in app code).
	- `README.md` – Project summary.

- Important entry points
	- API application: `server/http.py` exposes `app` (FastAPI) and registers routes and exception handlers.
	- App factory: `server/config/app.py:create_app()` builds the FastAPI app, sets OpenAPI metadata, and preloads TTS asynchronously on startup.
	- Routes:
		- `server/routes/health.py` – `GET /healthz`.
		- `server/routes/tts.py` – `POST /tts` (synthesize text).
		- `server/routes/voices.py` – `GET /tts/voices` (list voices; optional samples).
	- TTS core:
		- `tts/tts.py` – `Engine`, `TextToSpeechRequest`, `TextToSpeechResponse`.
		- `tts/kokoro_engine.py` – Kokoro implementation of `TTSEngineInterface` with async generation and voice preloading.
		- `tts/engine_interface.py` – Abstract engine contract.
		- `tts/voices.py` – Voice models/utilities and loader for `tts/kokoro_voices.json` (voice IDs are prefixed with `kokoro.`).

- How modules interact
	- Requests hit FastAPI routes → Pydantic models validate input → `Engine.from_voice_id()` selects engine (Kokoro) → engine generates WAV bytes → response serializes audio as base64.
	- `server/config/app.py` schedules `Engine.preload_async()` on startup to warm voices using a thread pool controlled by `AsyncConfig`.
	- Errors are normalized via handlers in `server/exceptions/handlers.py`.

## 2) Development Environment Setup

- System requirements
	- Python 3.12+
	- `uv` package manager (recommended; `uv.lock` present). Pip also works.
	- OS library for audio: libsndfile (required by `soundfile`). On Debian/Ubuntu: `libsndfile1`.
	- Optional: Docker (only needed if you plan to run Postgres from `docker-compose.yaml`; the app doesn’t currently use the DB).

- Install dependencies
	- Using uv (recommended):
		```bash
		uv sync
		```
	- Using pip (fallback):
		```bash
		python -m venv .venv
		source .venv/bin/activate
		pip install -e .
		```
		Note: `pip install -e .` reads dependencies from `pyproject.toml`.

- Configure environment variables (all optional; defaults shown)
	- `TTS_THREAD_POOL_MAX_WORKERS` (int, default: `4`)
	- `TTS_GENERATION_TIMEOUT` (float seconds, default: `30.0`)
	- `VOICE_PRELOAD_TIMEOUT` (float seconds, default: `120.0`)
	- `MAX_CONCURRENT_VOICE_SAMPLES` (int, default: `10`)

- Run the API locally
	```bash
	uv run uvicorn server.http:app --reload --log-level debug
	```
	Then open: Swagger UI at http://127.0.0.1:8000/docs or ReDoc at http://127.0.0.1:8000/redoc

## 3) Coding Standards & Conventions

- Style & typing
	- Follow PEP 8 and prefer full type hints. Use docstrings on public functions/classes.
	- Pydantic models define API schemas and serialization behavior (see `TextToSpeechRequest/Response`, `Voice`).
	- Use FastAPI routers in `server/routes/` and keep handlers async.

- Formatters/linters
	- Recommended (not enforced yet): Black (format), Ruff (lint), and Mypy (types).
	- Example (if installed):
		```bash
		uv run ruff check .
		uv run ruff format .
		uv run mypy .
		```

- Naming
	- Modules/files: `snake_case.py`; variables/functions: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
	- API routes use singular resources and clear tags (e.g., `tts`, `voice`).

- Folder structure rules
	- Keep FastAPI entry in `server/http.py`, app wiring in `server/config/`, and endpoints in `server/routes/`.
	- TTS engines live in `tts/` and implement `TTSEngineInterface`.
	- Voice metadata goes in `tts/kokoro_voices.json` with IDs prefixed by the engine namespace (e.g., `kokoro.af_heart`).

- Comments / docs
	- Prefer concise docstrings; reference request/response examples and error cases.
	- Update OpenAPI tags/descriptions in `create_app()` when adding new domains.

## 4) Testing

- Framework
	- Use `pytest` (recommended). Add `pytest` as a dev dependency locally.

- Run tests
	```bash
	uv run pytest -q
	```

- Example: minimal tests
	- Health endpoint using FastAPI’s TestClient:
		```python
		# tests/test_health.py
		from fastapi.testclient import TestClient
		from server.http import app

		client = TestClient(app)

		def test_healthz():
				r = client.get("/healthz")
				assert r.status_code == 200
				assert "version" in r.json()
		```

- Coverage expectations
	- Target ≥80% on changed code for features/bug fixes. Include happy path + at least one failure path (e.g., invalid `voice_id`).

## 5) Common Workflows

- Add a new API endpoint
	1) Create a router in `server/routes/<feature>.py` and define handlers.
	2) Register it in `server/http.py` via `app.include_router(...)`.
	3) Add a tag/description in `create_app()` if it’s a new domain.
	4) Add tests and update docs/examples.

- Add a new TTS engine
	1) Create `tts/<engine>_engine.py` implementing `TTSEngineInterface`.
	2) Register it in `Engine._initialize_engines()` and route via `Engine.from_voice_id()` using a prefix (e.g., `myengine.`).
	3) Provide voice metadata and samples (if applicable).
	4) Add tests for generation, preloading, and error paths.

- Add or update a voice
	1) Edit `tts/kokoro_voices.json` (IDs will be auto-prefixed with `kokoro.`).
	2) Verify with `GET /tts/voices` and optional `include_samples=true`.

- Fix a bug
	1) Reproduce with a failing test.
	2) Fix with smallest change; keep behavior compatible.
	3) Add regression test and update docs if behavior changed.

- Migrations
	- Not applicable. The app does not use a database yet (Postgres compose is present but unused).

- Pre-PR quality checks
	```bash
	uv run ruff check .
	uv run ruff format .  # or black . if you prefer
	uv run mypy .
	uv run pytest -q
	```

## 6) Debugging & Logs

- Run in debug
	```bash
	uv run uvicorn server.http:app --reload --log-level debug
	```

- Logs
	- Uvicorn/FastAPI logs go to stdout/stderr. Exception handlers return structured JSON errors.
	- For heavy troubleshooting, add temporary `logging.debug(...)` in code paths (e.g., around generation or preload), then remove before merging.

- Tools
	- Swagger UI at `/docs` to try requests.
	- `httpie` or `curl` for quick checks:
		```bash
		http :8000/healthz
		http POST :8000/tts text="Hello" voice_id="kokoro.af_heart"
		```

## 7) Performance & Pitfalls

- Known hotspots
	- TTS generation is CPU-bound and runs in a `ThreadPoolExecutor`. Avoid blocking the event loop; keep handlers async.
	- Voice preloading can be slow; it runs on startup in the background with a timeout.

- Guidelines
	- Avoid long synchronous work in route handlers; use executors or async functions.
	- Keep payloads reasonable. Audio is base64-encoded; `include_samples=true` on `/tts/voices` increases response size and latency.
	- Tune via env vars: thread pool size, generation timeout, preload timeout, and concurrent sample limit.

- Patterns to avoid
	- Don’t call CPU-bound work directly in async functions without an executor.
	- Don’t use raw voice IDs without the engine prefix (use `kokoro.<id>` from `/tts/voices`).

## 8) Contribution Guide

- Branch naming
	- `feat/<short-desc>`, `fix/<short-desc>`, `docs/<short-desc>`, `chore/<short-desc>`

- Commit messages (Conventional Commits)
	- `feat: add X`, `fix: correct Y`, `docs: update onboarding`, `refactor: ...`, `test: ...`

- PR process
	- Keep PRs focused and small. Include tests for new behavior.
	- Ensure local checks pass (lint/format/type/test). At least one approval recommended.

- Code review expectations
	- Clear description, testing notes, and any perf or risk implications. Respond to feedback promptly.

## 9) Example Code Snippets

- Programmatic synthesis using models
	```python
	from tts import TextToSpeechRequest

	req = TextToSpeechRequest(text="Hello, world!", voice_id="kokoro.af_heart")
	resp = await req.execute_async()
	audio_b64 = resp.model_dump()["audio"]
	```

- Minimal new endpoint pattern
	```python
	# server/routes/ping.py
	from fastapi import APIRouter
	router = APIRouter()

	@router.get("/ping", tags=["health"])  # reuse health tag or add a new one
	async def ping():
		return {"pong": True}

	# Register in server/http.py
	# app.include_router(ping_router)
	```

- Do vs Don’t (async + CPU-bound work)
	```python
	# DON’T – blocks the event loop
	async def handler(text: str):
			return KokoroEngine.get_instance()._generate_audio(text, "kokoro.af_heart")

	# DO – use async entry points that offload to a thread pool
	async def handler(text: str):
			engine = Engine.from_voice_id("kokoro.af_heart")
			return await engine.generate_async(text, "kokoro.af_heart")
	```

---

Quick reference
- Run: `uv run uvicorn server.http:app --reload`
- Health: `GET /healthz`
- Voices: `GET /tts/voices?include_samples=false`
- TTS: `POST /tts` with `{ "text": "...", "voice_id": "kokoro.af_heart" }`

Requirements coverage
- Codebase overview: Done
- Dev setup: Done
- Coding standards: Done
- Testing: Done (examples + expectations)
- Common workflows: Done
- Debugging/logs: Done
- Performance/pitfalls: Done
- Contribution guide: Done
- Example snippets: Done

