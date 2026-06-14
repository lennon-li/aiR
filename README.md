# aiR — AI-Powered R Analysis Copilot

An agent-guided companion for R-based statistical analysis. The AI agent proposes analysis steps, writes R code, and interprets real execution results — while the analyst stays in control of every decision.

Live at **[air.biostats.ai](https://air.biostats.ai)**.

---

## What it does

You describe an analysis objective. The agent:
1. Shapes vague objectives into concrete statistical questions
2. Proposes the next analysis step and writes R code
3. Executes code (depending on mode) via a persistent R session
4. Interprets only real execution output — never fabricates results

Three modes control how much the agent does automatically:

| Mode | Behaviour |
|------|-----------|
| **Guided** | Agent proposes and explains. You review and send to console. |
| **Balanced** | Agent auto-executes safe inspection commands (`summary`, `head`, `str`). |
| **Autonomous** | Agent writes and executes code directly. Chat stays minimal. |

---

## Architecture

```
Browser
  └── air-web (Cloud Run · Next.js)
        └── air-api (Cloud Run · FastAPI)
              ├── Google Conversation Agent (Dialogflow CX)
              │     └── Vertex AI Search  ← RAG over R package docs
              ├── air-r-service (Cloud Run · R/Plumber)
              │     └── persistent R session + GCS state
              └── GCS session bucket  ← execution context memory
```

### Services

- **`web/`** — Next.js frontend. Chat pane, code console, plot/output viewer, mode selector.
- **`api/`** — FastAPI orchestration layer. Handles session management, mode policy, R code extraction, execution gating, anti-hallucination filtering, and GCS persistence.
- **`r-service/`** — R/Plumber microservice. Runs R code, maintains session state across turns, returns stdout/plots/environment.

### Key design choices

**Anti-hallucination gate** — The agent is not allowed to claim code ran or objects exist unless `air-api` confirms real execution from `air-r-service`. Phrases like "I ran the code" or "the result shows" are flagged if no real output is present.

**Execution policy** — `api/policy_engine.py` maps the analysis mode to a behaviour profile (explanation depth, auto-execute rules, interaction level). The policy is enforced by `air-api`, not the agent.

**RAG over R docs** — The agent is grounded via Vertex AI Search over curated R package documentation (`grounding_docs/`): dplyr, ggplot2, tidyr, data.table, purrr, readr, stringr, and general R style/performance guides.

**Session-scoped GCS memory** — Execution results are stored in GCS keyed by session UUID and injected as context in follow-up turns, so the agent can interpret real prior output without re-running code.

---

## Repository layout

```
api/              FastAPI backend (orchestration, policy, sessions)
  tools/          R execution tool
r-service/        R/Plumber execution microservice
web/              Next.js frontend
  src/app/        Pages and API client
  e2e/            Playwright end-to-end tests
grounding_docs/   R package docs indexed in Vertex AI Search (RAG source)
shared/           Shared data models
schemas/          JSON schemas (future structured output)
data/             Sample data catalog
scripts/          Deploy and verification scripts
docs/             Architecture, deployment, and operating notes
infra/            Cloud Run deploy scripts
```

---

## Deployment

All three services run on **Google Cloud Run** in project `air-mvp-lennon-li-2026`. The Conversation Agent runs on **Vertex AI Agent Builder / Dialogflow CX** (agent ID `1e9ad1e9-30bb-45ad-98e1-16714da84164`, global location).

See `docs/DEPLOYMENT.md` for deployment steps and `docs/ARCHITECTURE.md` for the full service diagram.
