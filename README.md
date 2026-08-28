# Autonomous Research Lab

An experimental, progressively-built agentic AI research system. A user submits a
research question; the system autonomously plans, delegates to specialized agents,
uses tools, gathers evidence, challenges its own conclusions, evaluates its own
research quality, and produces a traceable, inspectable final answer.

Built incrementally across 11 versions, each teaching one core agentic AI concept,
with every run fully observable via a Postgres-backed execution trace.

This is **not** a chatbot or a RAG app.

---

## 1. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 (developed on Windows / PowerShell) |
| API | FastAPI — `app/api/main.py` — single `/research` endpoint + `/health` |
| LLM provider | Ollama (local, free), model `llama3.2:3b`, running in Docker |
| Embeddings | `nomic-embed-text` via Ollama |
| Database | PostgreSQL 18 (`postgres:latest`) via Docker, SQLAlchemy async + asyncpg |
| Web search | Tavily API (free tier) |
| Packaging | `pyproject.toml`, `pip install -e ".[dev]"` |

**Not implemented despite interface support:** Groq and Anthropic model providers.
`ModelInterface` is provider-agnostic, but `OllamaProvider` is the only concrete
implementation.

---

## 2. Getting started

```powershell
# 1. Start infra
docker compose up -d

# 2. Install the project (editable, with dev deps)
pip install -e ".[dev]"

# 3. Copy the env template and fill in your own keys
copy .env.example .env

# 4. Run the API
uvicorn app.api.main:app --reload

# 5. Hit the one real endpoint
# POST http://localhost:8000/research   {"question": "..."}
# Swagger UI: http://localhost:8000/docs
```

`docker-compose.yml` defines two services: `postgres` and `ollama`. The Ollama
volume is declared `external: true, name: ollama` so it reuses a pre-existing
volume with the model already pulled — if you're on a fresh machine, pull the
model into that named volume first or the API calls will 404.

### ⚠️ Before you commit or share this project anywhere

This repo's `.env` has, in the past, contained a **live Tavily API key**. Rotate
that key at app.tavily.com if it was ever shared, zipped, or pushed. Going
forward:

- Never zip/export the project without excluding `.env` (`zip -x '*.env*' ...`).
- Confirm a `.gitignore` exists and lists `.env`.
- Run `git ls-files | grep .env` — if that prints anything, the file is tracked
  and needs `git rm --cached .env` (plus a key rotation, which you should do
  either way).

---

## 3. Project structure

```
app/
  api/main.py                — FastAPI app, /research and /health endpoints
  agents/
    research_agent.py         — core single-agent execution loop (V1)
    planner.py                 — task decomposition (V2)
    orchestrator.py             — main pipeline: plan → research → fact-check →
                                    critique → draft → challenge → synthesize,
                                    with V9 strategy branching
    dynamic_orchestrator.py      — V10: LLM-generated research teams (separate
                                    from Orchestrator)
    strategy_selector.py          — V9: classifies question → fast/standard/rigorous
    team_composer.py               — V10: generates specialist roles dynamically
    roles.py                        — all system prompts (Researcher, Fact Checker,
                                        Critic, Challenger, Synthesizer, Updated
                                        Synthesizer)
  models/
    base.py                    — ModelInterface ABC, Message, ModelResponse, ToolCall
    ollama_provider.py          — the only implemented provider
  tools/
    base.py                     — Tool ABC, ToolRegistry
    calculator.py                 — safe eval() with character allowlist
    web_search.py                   — Tavily integration
    fetch_page.py                     — HTML text extraction, hand-rolled parser
  evidence/schemas.py               — Claim, Evidence, ResearchAnswer
                                        (claims population is a known gap — see §6)
  observability/
    models.py                          — RunRecord, StepRecord, MemoryRecord,
                                          EvaluationRecord, FailureAnalysisRecord
    trace.py                            — TraceRecorder (writes steps live)
  memory/
    embeddings.py                        — Ollama embedding client
    similarity.py                          — cosine similarity
    store.py                                — MemoryStore: store() + retrieve_relevant()
  evaluation/
    deterministic.py                         — trace-based heuristic scoring (V7)
    llm_judge.py                               — LLM-scored factual_accuracy/reasoning_quality
    evaluator.py                                — combines both into weighted overall_score
    failure_detector.py                          — threshold-based flagging (V8)
    root_cause.py                                 — LLM-assisted root cause + recommendation
    failure_analysis_service.py                    — ties V8 together
  experiments/
    benchmark.py                                    — V11: strategies × questions, evaluated
    report.py                                        — benchmark comparison report
  infrastructure/db.py                                — async engine, session factory, init_db()
  config/settings.py                                    — Pydantic Settings, loads .env

tests/   (manual scratch scripts, not a real pytest suite)
  scratch_test*.py — one script per version, V1 through V11
```

---

## 4. Version status

Kept intentionally honest — a claim only moves to "verified" once real pasted
output confirmed it, not just "the code exists."

| Ver | Concept | Code | Verified? |
|---|---|---|---|
| V1 | Single agent, tools, budgets, trace, API | ✅ | ✅ Fully verified |
| V2 | Planning + execution | ✅ | ✅ Fully verified |
| V3 | Memory (embeddings, retrieval) | ✅ | ⚠️ Write path confirmed; injection into task prompts confirmed by code inspection (see §7) but not yet re-confirmed via a live trace |
| V4 | Multi-agent (Researcher/FactChecker/Critic/Synthesizer) | ✅ | ✅ Fully verified |
| V5 | Parallel research (asyncio.gather, isolated DB sessions) | ✅ | ⚠️ Correctness fix required — see §7, item 1. Performance benefit not yet measured |
| V6 | Adversarial Challenger | ✅ | ✅ Fully verified after a real bug fix (see §5, #10) |
| V7 | Self-evaluation (deterministic + LLM judge) | ✅ | ❌ Never run |
| V8 | Failure analysis / root cause | ✅ | ❌ Never run (depends on unverified V7 data) |
| V9 | Adaptive strategy selection | ✅ | ⚠️ Exercised without error; classification accuracy not spot-checked |
| V10 | Dynamic team generation | ✅ | ⚠️ First test case verified end-to-end; second test case unconfirmed |
| V11 | Architecture/strategy benchmarking | ✅ | ❌ Never run |

---

## 5. Known bugs — fixed

1. Windows `python3` alias broken → use `python`, disabled the Store execution alias.
2. `.env` and `.idea/` were committed to git → added to `.gitignore`, `git rm --cached`.
3. `ModuleNotFoundError: app` → stale/uninitialized `.venv` → fixed via `pip install -e ".[dev]"`.
4. Ollama model 404 → Compose was creating a new empty volume → fixed with `external: true, name: ollama`.
5. Pydantic validation error on `ModelResponse.raw` → newer `ollama` package returns a typed `ChatResponse`, not a dict → fixed with `.model_dump()`.
6. Postgres crash: v18 volume format incompatibility with a stale v16 volume → deleted the old volume, let v18 init fresh.
7. `WebSearchTool.execute()` — `min(kwargs.get("max_results", 5), 10)` threw `TypeError` when the LLM passed `max_results` as a string → fixed with explicit `int()` coercion + fallback. **Most valuable bug in the project — found by actually running V6, not by inspection.**

## 5b. Known bugs — found in review, fix in `app/agents/orchestrator.py` and `app/models/ollama_provider.py`

8. **[High severity] Shared `AsyncSession` across parallel tasks in V5.** In
   `_run_task_isolated`, memory *reads* (`memory.retrieve_relevant(...)`) used the
   single `AsyncSession` created once in `main.py` and shared across every
   concurrently-running task in `asyncio.gather(...)`. SQLAlchemy's `AsyncSession`
   is not safe for concurrent use by multiple coroutines — this can throw
   (`IllegalStateChangeError`) or silently misbehave whenever a plan has more than
   one task. Memory *writes* already used a fresh per-call session and were fine.
   **Fix:** give reads their own isolated session too, matching the write path.
9. **[Low severity] `OllamaProvider.generate` drops `tool_call_id`/`name` on every
   call** when re-serializing message history, and doesn't resend the assistant's
   own prior `tool_calls`. Ollama's API tolerates this today, but it means the
   model never sees why it called a tool, only the raw result. Worth fixing before
   ever adding a stricter provider (e.g. wiring up the Anthropic option that's
   already stubbed in settings).

---

## 6. What's explicitly not built

- Groq and Anthropic model providers (interface supports it, only Ollama implemented).
- Real `Claim`/`Evidence` population — `/research` always returns `claims=[]`.
- A real pytest suite — all testing is manual `scratch_test_*.py` scripts.
- Alembic migrations — tables are created via `Base.metadata.create_all()` only.
- pgvector or any real vector database — memory similarity is an O(n) linear scan in Python.
- Any UI/research console — Swagger `/docs` is the only interface used.
- Security hardening beyond basic budgets — no auth, no rate limiting, no sandboxing
  beyond the calculator's `eval()` character allowlist.
- Memory pruning/compression — the `memory` table accumulates test junk over time.

---

## 7. Recommended next steps, in priority order

1. **Apply the V5 session fix (§5b, #8)** before running V5/V9/V10/V11 again — this
   is the one bug that will actively corrupt or crash multi-task runs.
2. **Actually run and verify V7 and V8.** In particular, sanity-check the LLM
   judge: does it produce meaningfully different scores for a clearly good vs.
   clearly bad run, or does it just always return ~0.7?
3. **Re-confirm V3's memory injection live.** The code path is correct (task
   prompts do get a `"Relevant prior findings:"` block appended when relevant
   memories exist), but re-run it and query `steps.input_data` for that string to
   see it in a real trace rather than trusting static code review alone.
4. **Consolidate to one project folder.** Two copies (`C:\Users\...\autonomous-research-lab`
   vs `Downloads\autonomous-research-lab`) caused repeated environment confusion.
5. **Audit other tool-argument-consuming code for the same int/str coercion
   pattern** that hit `web_search.py`. (`fetch_page.py` was checked — it only
   takes a `url` string, so it's not at risk.)
6. **Finish V10's second test case** (the quantum-computing question) — it
   appeared to run long or get cut off and was never confirmed complete.
7. Only then treat V11's benchmark numbers as meaningful.

---

## 8. A note on how this document was produced

Sections 1–4 and 6 reflect the project's own build log. Section 5b was added
after an independent code review of the uploaded source (not just the prior
status notes) — those two items were verified by reading the actual files, not
assumed from documentation claims. Treat "verified" the same way the rest of
this doc does: it means someone actually ran it and looked at the output, not
that the code merely exists.