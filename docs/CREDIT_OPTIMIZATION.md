# GenAI App Builder Credit Optimization

## Objective
Utilize the $1,300+ GenAI App Builder credits by routing all agent reasoning and grounding tasks through the `discoveryengine.googleapis.com` ecosystem (Vertex AI Search & Conversation).

## Architectural Shift
The application has moved from a "Direct Model Call" pattern to a "Grounded Reasoning" pattern.

### 1. Credit-Eligible Grounding
- **Service:** Vertex AI Search (Discovery Engine)
- **API Call:** `converse_r_docs` (using the `answer` endpoint).
- **Billing:** Every call to the Search API is billed against the App Builder credits.

### 2. Implementation Details
- **Orchestrator:** `api/llm_orchestrator.py` now performs a proactive search via `converse_r_docs` at the start of every analysis turn.
- **Context Injection:** The results from the Search Engine are injected into the model's prompt as the primary source of truth.
- **Model:** Switched to **Gemini 2.5 Flash** (stable) in `us-central1` for low-latency reasoning on top of the grounded context.

### 3. Verification
- Credits can be monitored in the Google Cloud Console under **Billing -> Credits**.
- The `air-api` logs now include a `credit_eligible: True` flag in `chat_request` telemetry events.

## Maintenance
- Ensure the Data Store `r-docs-store_1776610230621` remains active.
- New R packages should be added to the Data Store rather than the system prompt to maintain credit eligibility.
