# aiR Architecture

## Purpose

aiR is an R analysis copilot web app. It combines:
- a web UI,
- a backend orchestration layer,
- a Google Conversation Agent for dialogue/planning,
- an R execution service,
- GCS-backed session memory.

## Current service architecture

air.biostats.ca
  -> air-web on Cloud Run
  -> air-api on Cloud Run
      -> Google Conversation Agent / Dialogflow CX for dialogue and goal shaping
      -> air-r-service on Cloud Run for real R execution
      -> GCS for session execution memory

## Cloud Run services

- air-web
  - Frontend / Next.js UI.
  - Hosts setup screen, chat, console, plot/output panes.
  - Sends chat/session requests to air-api.

- air-api
  - Backend orchestration layer.
  - Handles mode mapping: guided, balanced, autonomous.
  - Calls Conversation Agent.
  - Extracts R code.
  - Applies execution policy.
  - Calls air-r-service when execution is allowed.
  - Stores execution output in GCS for follow-up context.

- air-r-service
  - R/Plumber execution service.
  - Runs R code.
  - Maintains/persists R session state.
  - Returns stdout/stderr/artifacts.

- air-r-backend
  - Older/legacy R backend.
  - Should not be used unless explicitly confirmed.
  - Before deleting, verify no env vars or code paths reference it.

## Google Conversation Agent

Project:
air-mvp-lennon-li-2026

Location:
global

Agent ID:
1e9ad1e9-30bb-45ad-98e1-16714da84164

Role:
The Conversation Agent is the dialogue/planning layer only. It should not be treated as the whole app brain.

Important:
- It may suggest R code.
- It may shape vague objectives into statistical questions/hypotheses.
- It must not claim R code was executed unless air-api/air-r-service confirms execution.
- It must not fabricate R output.

## Correct responsibility split

Conversation Agent:
- understands user intent,
- guides the analysis,
- asks clarifying questions for vague objectives,
- writes concise R code,
- interprets real stored output when provided.

air-api:
- decides whether code should execute,
- enforces slider/mode policy,
- extracts R code,
- calls air-r-service,
- stores execution output,
- injects real execution context into follow-up turns.

air-r-service:
- actually runs R code,
- creates/modifies R objects,
- returns real output.

web:
- displays concise chat,
- displays code,
- sends code to console depending on mode,
- avoids duplicating long R output in chat.

## Mode behavior

Guided:
- Propose the next analysis step.
- Explain why.
- Provide R code.
- Do not auto-execute.
- Show Send to Console.
- Do not claim objects exist unless user has executed code.

Balanced:
- Concise explanation and R code.
- May auto-execute safe inspection commands if policy allows.
- Avoid unnecessary questions.

Autonomous:
- Generate R code.
- Send safe R code directly to air-r-service.
- Keep chat short.
- Do not duplicate long R output in chat.
- Store output for follow-up interpretation.

## Core rule

Chat explains intent.
Console shows computation.
Backend remembers results.
Agent interprets only real results.
