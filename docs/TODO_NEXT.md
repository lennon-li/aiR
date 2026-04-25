# aiR: Next Implementation Steps

## 1. Immediate Next Tasks
- [ ] **Stream UI Enabling:** Investigate a dedicated domain for the API to resolve persistent CORS issues with `text/event-stream` and enable the real-time streaming UI.
- [ ] **Expand Documentation Corpus:** Ingest official PDFs for `tidyr`, `purrr`, `stringr`, and `data.table` into the Discovery Engine Data Store to improve grounding breadth.
- [ ] **Cost Monitoring:** Set up a Cloud Monitoring dashboard to track the burn rate of the $1,300+ credits.

## 2. Completed in Latest Refactor (April 2026)
- [x] **Gemini 2.5 Flash Migration:** Upgraded from the retired 1.5/3.1 preview models for stability and speed.
- [x] **Credit Optimization:** Integrated Vertex AI Search (Discovery Engine) as the primary reasoning step for all queries.
- [x] **Auto-Scroll UX:** Refactored chat and console scroll logic to be more aggressive and reliable.
- [x] **E2E Stability:** Updated Playwright suite with `data-testid` selectors and 180s timeouts; 8/8 tests passing.
- [x] **Streaming Backend:** Implemented `call_agent_stream` generator to support future real-time UI.

## 3. Priority Order
1. **CORS/SSE Stability** (Enables the "alive" feeling of the agent).
2. **Corpus Expansion** (Makes the tool more useful for real data science).
3. **Credit Monitoring** (Ensures we are maximizing the $1,386 budget).

## 4. What NOT to Touch
- **Do not** revert the Discovery Engine integration; this is mandatory for credit consumption.
- **Do not** remove the `data-testid` attributes from `page.tsx`; they are essential for the 100% pass rate in E2E.
- **Do not** use Gemini 1.5 or 3.1 Pro unless confirmed as active/stable.

---
## How to Brief Copilot
When starting a new session with GitHub Copilot or another coding agent, use this prompt:
> *"Please read `docs/agent_context.md`, `docs/TODO_NEXT.md`, and `docs/CREDIT_OPTIMIZATION.md` before making any changes. We are working on a professional R copilot that must be grounded via Vertex AI Search to utilize GenAI App Builder credits."*
