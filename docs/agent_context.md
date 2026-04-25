# aiR Agent Context

## Project overview
aiR is an R copilot app for coding, learning, and execution in R.

In the UI:
- Product name: **aiR**
- Assistant label: **R copilot**

The app is designed to support a spectrum from direct execution to guided learning.

## Architecture
The project has three main services:

### 1) air-web
Frontend UI.
Responsible for:
- setup page
- workspace UI
- editor
- console
- R copilot chat panel
- plots / environment / history tabs
- slider controls
- reset controls
- upload flow

### 2) air-api
Backend control plane.
Responsible for:
- session creation and refresh
- chat routing
- grounding decisions
- forwarding execution requests
- telemetry/logging
- policy handling
- packaging responses for the frontend

### 3) air-r-service
R execution service.
Responsible for:
- executing R code
- returning stdout / errors
- persisting session state
- writing plot artifacts
- returning environment summaries

## Core UX / behavior

### Two-step flow
1. Setup page
2. Workspace

### Setup page
Includes:
- app intro
- objective input
- Learning <-> Doing slider
- file upload
- session initialization

### Workspace
Includes:
- top bar
- live policy slider in header
- context/memory bar
- code editor
- console
- R copilot chat
- right-side utilities/tabs:
  - Plots
  - Environment
  - History

### Slider behavior
The slider controls how the R copilot behaves, not whether execution exists.

Interpretation:
- lower end = more direct / execution-oriented
- higher end = more guided / explanatory / teaching-oriented

Broad mode bands:
- Doing
- Pair
- Guided
- Tutor / Coach end

### Auto-send behavior
In Doing / Pair modes, assistant-generated code may be auto-sent to execution only under constrained conditions.
Auto-send has been hardened and should only trigger when the response is clearly a single runnable code suggestion.

### Provenance
Execution provenance should be visible and honest, such as:
- You
- R copilot (auto)
- R copilot (manual)

### History
History stores executed code and related metadata.
History export should produce a clean `.R` script.

## Grounding and retrieval

### Docs grounding
Docs grounding exists and is currently based on Vertex AI Search / AnswerQuery style retrieval rather than raw Gemini publisher-model responses.

This means:
- it is stricter
- it is more extraction-based
- it is package-corpus dependent

### File grounding
File grounding exists.
The system can use uploaded session files as context.

### Important grounding rule
Grounding coverage depends on what documentation has been ingested.

If the user asks about a package that is not covered by the grounded docs corpus, the system should respond honestly with something like:

> I'm not grounded for that package yet. I can still try to help in a general way, but I don't have package documentation loaded for it.

Do NOT pretend unsupported packages are docs-grounded.

## Current MVP status

### Confirmed working
- setup -> workspace flow
- session creation
- signed session tokens
- policy-aware UI behavior
- code editor
- console
- R copilot panel
- plots / environment / history
- history export
- file uploads
- R execution path
- execution provenance
- telemetry/logging
- file grounding
- docs grounding for the current ingested corpus
- demo-ready UI polish

### Intentionally limited
- docs grounding only covers currently ingested packages/topics
- broad package coverage is not automatic
- AnswerQuery-style docs responses may be less conversational than a raw generative model

## Current docs-grounding direction
The current grounded corpus should focus on practical R work rather than all of CRAN.

Priority package families include:
- base R / datasets / stats / utils
- dplyr
- tidyr
- tibble
- readr
- stringr
- forcats
- purrr
- lubridate
- data.table
- janitor
- ggplot2
- optionally readxl / haven / scales

## Constraints for future work
- Prefer small targeted changes.
- Do not redesign the architecture unless explicitly asked.
- Preserve current MVP behavior where possible.
- Keep telemetry and provenance intact.
- Keep frontend and backend schemas aligned.
- Do not let logging/telemetry break core execution.
- Do not deploy without explicit approval.

## Agent editing guidance
Before changing anything:
1. inspect the real code
2. do not assume old summaries are still correct
3. verify the current behavior with a minimal test

When reporting:
- distinguish confirmed behavior from intended behavior
- report files changed
- explain exact logic changed
- provide verification steps and results

When unsure:
- ask
- or clearly mark the statement as unverified

When working on package-related behavior:
- distinguish grounded vs ungrounded package support honestly
- prefer "not grounded for that package yet" over "not trained"
