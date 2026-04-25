# Vertex AI Grounding Implementation Plan

## Objective
Implement the "Grounded Tutoring" feature specified in the MVP design by integrating Vertex AI Search (Agent Builder) into the Python Control Plane. This will provide the Gemini model with accurate R documentation, package help, and statistical theory to improve its teaching capabilities.

## Background & Motivation
Currently, the `/chat` endpoint in `api/main.py` relies solely on the base knowledge of the `gemini-1.5-flash-001` model. To fulfill the MVP's goal of being a robust Socratic tutor, the agent needs to be grounded in specific R documentation to reduce hallucinations and provide accurate, context-aware guidance. Per project guidelines, we must use Vertex AI Search (`discoveryengine.googleapis.com`) for this RAG implementation.

## Scope & Impact
- **Affected Files:**
  - `api/requirements.txt`: Add the `google-cloud-discoveryengine` library.
  - `api/vertex.py` (New): Encapsulate the Vertex AI Search logic.
  - `api/main.py`: Refactor the `/chat` endpoint to utilize the new `vertex.py` module.
  - `infra/deploy.ps1`: Update deployment scripts to include necessary environment variables (e.g., `DATA_STORE_ID`).
- **Impact:** The backend will gain the ability to retrieve relevant documents before generating a response, significantly improving the quality of the AI's guidance, especially for complex R packages.

## Proposed Solution
1.  **Dependency Update:** Add `google-cloud-discoveryengine` to `requirements.txt`.
2.  **`api/vertex.py` Module:** Create a dedicated module with a function `search_r_docs(query: str, project_id: str, location: str, data_store_id: str) -> str`. This function will query a configured Vertex AI Data Store and format the top results into a context string.
3.  **Backend Refactoring (`api/main.py`):**
    - Introduce a new environment variable `DATA_STORE_ID` to configure the target search app.
    - In the `/chat` endpoint, intercept the user's message, call `search_r_docs`, and append the retrieved context to the system instructions or as a prefixed context block before sending it to the Gemini model.
4.  **Deployment Update:** Modify `infra/deploy.ps1` to pass the `DATA_STORE_ID` to the `air-api` Cloud Run service.

## Alternatives Considered
- **Manual RAG (Vector DB + Embeddings):** Rejected. Project mandates explicitly state to prioritize Vertex AI Agent Builder (`discoveryengine.googleapis.com`) over manual RAG implementations to utilize GenAI App Builder credits.
- **Raw Web Search (Google Search Grounding):** While possible via the Gemini API, using a dedicated Vertex AI Search Data Store allows us to curate the specific R documentation and statistical texts we want the agent to rely on, ensuring higher quality and domain relevance.

## Implementation Steps
1.  **Update Dependencies:** Append `google-cloud-discoveryengine` to `api/requirements.txt`.
2.  **Create `api/vertex.py`:** Implement the `discoveryengine` client to query the search app and extract the `extractive_answers` or `snippets` from the response.
3.  **Refactor `api/main.py`:** 
    - Read `DATA_STORE_ID` from the environment.
    - Update the `/chat` route to fetch context and inject it into the prompt.
4.  **Update Infrastructure:** Modify `infra/deploy.ps1` to prompt for or hardcode the `DATA_STORE_ID` during deployment.

## Verification & Testing
- **Local Testing:** Run the API locally with a valid `DATA_STORE_ID` and send a query (e.g., "How does dplyr::mutate work?"). Verify in the logs that the search engine is queried and returns relevant snippets.
- **End-to-End Test:** Deploy the updated Control Plane and use the web UI to ask a specific R documentation question. Verify the response is accurate and grounded in the provided context.

## Prerequisites / Blockers
- **Data Store Creation:** A Vertex AI Search Data Store containing R documentation must be created in the GCP Console before this feature can be fully tested. We will assume the Data Store ID will be provided via environment variables.
