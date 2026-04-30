# Lessons Learned

## 1. Messenger widget is not app integration

Mistake:
The Google Conversational Messenger snippet was treated as if it connected the existing aiR chat UI to the agent.

Why it was wrong:
df-messenger creates a separate Google chat widget, either bubble or panel. It does not power the existing aiR chat box.

Fix:
Remove df-messenger code from aiR. Use air-api to call Dialogflow CX / Conversation Agent detectIntent and render the response in the existing aiR chat UI.

Prevention:
Do not add df-messenger unless the intended product is a separate Google Messenger UI.

## 2. Conversation Agent is not the whole app brain

Mistake:
The Conversation Agent was allowed to behave like a generic chatbot, producing verbose answers and imagined R results.

Why it was wrong:
aiR is an R copilot. R computation must happen in air-r-service. The agent must not claim objects exist or results are known unless execution actually happened.

Fix:
Keep air-api as the orchestrator. Use the Conversation Agent for planning/dialogue, but use air-api for execution policy and air-r-service for real computation.

Prevention:
Always preserve this split:
agent plans, backend orchestrates, R service computes.

## 3. Mock execution is not production verification

Mistake:
Logic was verified in MOCK mode and described as completed.

Why it was wrong:
The critical path is real deployed air-api calling real air-r-service. Mock tests do not prove session persistence, service authentication, R execution, or follow-up grounding.

Fix:
Require deployed endpoint tests against real Cloud Run services.

Prevention:
No runtime test, no acceptance. Mock tests are not sufficient for production sign-off.

## 4. Local auth cannot prove private Cloud Run service access

Mistake:
Local testing failed with “Could not retrieve identity token,” causing confusion.

Why it happened:
The private air-r-service requires Cloud Run service account identity. Local user context may not have the same token flow.

Fix:
Deploy air-api to Cloud Run and test from the Cloud Run service account context.

Prevention:
For private service-to-service Cloud Run calls, final verification must run from the deployed calling service or use proper service account impersonation.

## 5. Shell mismatch: bash commands in PowerShell

Mistake:
Used commands such as:
ls -R . | grep -i "lesson\|learned"

Why it was wrong:
The environment is Windows PowerShell. grep is not available by default.

Fix:
Use PowerShell-native commands:
Get-ChildItem -Recurse | Where-Object { $_.Name -match "lesson|learned" }

Prevention:
Default to PowerShell. Do not use grep/sed/awk/find/xargs/rm -rf unless bash/Linux/WSL/macOS is explicitly confirmed.

## 6. Recursive search over node_modules wasted time

Mistake:
Ran broad recursive search without excluding dependency/build folders.

Why it was wrong:
It searched web/node_modules and produced thousands of irrelevant matches.

Fix:
Exclude generated/dependency folders:
node_modules, .next, dist, build, .git, renv, .Rproj.user, __pycache__, .venv

Prevention:
Never run broad recursive text search without exclusions.

## 7. Startup was allowed to block the UI

Mistake:
START SESSION and “I’m just taking a peek” could take too long because the UI waited on multiple backend services.

Why it was wrong:
The user should enter the workspace quickly. Agent/R initialization should not freeze the whole interface.

Fix:
Open workspace quickly, then initialize Conversation Agent and R service in the background with visible status messages.

Prevention:
Do not block workspace rendering on non-essential startup tasks.

## 8. Agent asked too many questions for clear tasks

Mistake:
For “simulate me a df with 3 cols,” the agent asked for column types and row count.

Why it was wrong:
The user gave a simple safe operational request. The agent should make reasonable defaults.

Fix:
Adopt rule:
Clear task -> code.
Unclear objective -> shape the question.

Prevention:
Only ask clarification when the statistical objective is vague, variables are ambiguous, action is risky, or a decision materially changes the analysis.

## 9. Execution output was duplicated in chat

Mistake:
The chat displayed long summaries/results instead of keeping the chat concise.

Why it was wrong:
aiR has a console/output pane for computation. Chat should guide and interpret, not duplicate long console output.

Fix:
Store execution output as hidden context and show only short status in chat.

Prevention:
Chat explains intent. Console shows computation. Backend remembers results.
