# OPERATING_RULES

These rules must be followed for all work on the aiR project.

## 1) Assumptions and verification
- Do not make assumptions.
- Do not fill gaps with plausible guesses.
- If something is not verified from code, logs, config, deployment output, API responses, or my direct message, label it as unverified.
- Separate all findings into:
  - Confirmed facts
  - Hypotheses
  - What was checked
  - What remains uncertain
- If unsure, ask a focused question instead of guessing.

## 2) Debugging method
- For debugging, start with the smallest reproducible test.
- Show the raw error message, log output, response body, or failing command before proposing a root cause.
- Identify the exact failing layer before changing code.
- Compare expected behavior vs actual behavior.
- After a fix, rerun the same minimal test.
- Do not claim something is fixed unless the verification actually passed.

## 3) Deployment safety
- Do NOT deploy automatically.
- Do NOT run deployment commands unless Lennon explicitly approves deployment in the current conversation.
- Before any deployment, first explain:
  1. what will be deployed
  2. why deployment is needed
  3. which services/files will change
  4. how success will be verified
- Then stop and ask for approval.
- If approval is not explicit, do not deploy.

## 4) Change style
- Prefer the smallest practical change.
- Do not redesign architecture unless explicitly asked.
- Do not refactor unrelated code while fixing a bug.
- Preserve the current deployed MVP behavior unless a change is required to fix a confirmed problem.

## 5) Reliability rules
- Telemetry, logging, analytics, badges, and optional features must never break the core user path.
- Core execution, chat, and session behavior must continue working even if telemetry fails.
- Error handling should expose useful failure details instead of generic messages when safe to do so.

## 6) Reporting requirements
After making changes, always report:
1. Confirmed facts
2. Hypotheses
3. Files changed
4. Exact logic or patch applied
5. Verification steps run
6. Actual verification results
7. What remains uncertain

## 7) Honesty rules
- If a fix is only a hypothesis, say: "This is a hypothesis, not yet confirmed."
- If verification fails, say so clearly.
- Do not infer success from a plausible explanation.
- Do not say "done" or "fixed" without evidence.

## 8) Project-specific guardrails
- Keep frontend, API, and R service behavior aligned.
- Keep provenance, telemetry, and UI labels honest.
- Distinguish grounded vs ungrounded behavior clearly.
- If a package is not covered by the docs corpus, say it is not grounded for that package yet.
