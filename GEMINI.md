# aiR Project Gemini Instructions

## Priority

These aiR project rules override generic extension examples when working in this repository.

## Shell

Default shell is Windows PowerShell.

Do not use bash/Linux commands unless Lennon explicitly says Git Bash, WSL, Linux, or macOS.

Do not use:
- grep
- sed
- awk
- find
- xargs
- rm -rf
- chmod
- chown
- ls -R

Use PowerShell equivalents:
- Get-ChildItem
- Select-String
- Where-Object
- Get-Content
- Remove-Item

PowerShell examples:

Search files:
Get-ChildItem -Recurse -File |
  Where-Object {
    $_.FullName -notmatch '\\node_modules\\|\\.next\\|\\dist\\|\\build\\|\\.git\\|\\renv\\|\\.Rproj\\.user\\|__pycache__|\\.venv\\'
  } |
  Select-String -Pattern "pattern"

Find files by name:
Get-ChildItem -Recurse -File |
  Where-Object {
    $_.FullName -notmatch '\\node_modules\\|\\.next\\|\\dist\\|\\build\\|\\.git\\|\\renv\\|\\.Rproj\\.user\\|__pycache__|\\.venv\\'
  } |
  Where-Object {
    $_.Name -match "pattern"
  }

## Search discipline

Never run broad recursive searches without excluding:
- node_modules
- .next
- dist
- build
- .git
- renv
- .Rproj.user
- __pycache__
- .venv

If search results include dependency/build folders, stop immediately and rerun a narrower search.

## Status responsiveness

When Lennon asks “what is happening?”, “why is this taking so long?”, “are you stuck?”, or asks for status:

Stop work immediately and respond within 10 seconds.

Use this format:

Status:
- Current task:
- Current stage:
- Last completed action:
- Blocking issue:
- Next action:

Do not run more commands before the first status unless the current state is completely unknown.

## Permission and deployment

Never deploy without explicit approval.

However, once Lennon explicitly approves a specific aiR deployment/testing task in the current conversation, do not ask again for every safe verification step.

Allowed without repeated approval after task approval:
- reading files
- searching files
- checking Cloud Run service settings
- checking logs
- running endpoint tests
- rerunning failed non-destructive tests
- deploying the specifically approved service
- verifying GCS test-session objects

Still ask before:
- deleting services
- deleting buckets or production data
- changing DNS
- changing IAM
- changing billing/cost settings
- changing Cloud Run min instances
- deploying additional services not already approved
- overwriting user data

## Deployment discipline

Only deploy services whose source changed.

- api/ changes -> deploy air-api only
- web/ changes -> deploy air-web only
- R service changes -> deploy air-r-service only
- documentation-only changes -> do not deploy

Before deploying, state:
- service
- exact command
- why deployment is needed

## aiR architecture

air.biostats.ca
  -> air-web on Cloud Run
  -> air-api on Cloud Run
      -> Google Conversation Agent / Dialogflow CX for dialogue and goal shaping
      -> air-r-service on Cloud Run for real R execution
      -> GCS for session execution memory

Conversation Agent plans.
air-api orchestrates and enforces mode policy.
air-r-service computes.
GCS stores session-scoped execution memory.
web displays chat/code/console.

Do not reintroduce df-messenger unless explicitly requested.

## aiR behavior

Clear task -> write R code.
Unclear objective -> help shape the objective/statistical hypothesis.

Guided:
- propose next step
- explain why
- provide R code
- do not auto-execute

Balanced:
- concise code
- safe inspection may auto-execute if policy allows

Autonomous:
- write R code
- send safe code to R directly
- keep chat concise
- store execution output as hidden context

Never claim R code ran unless air-r-service actually executed it.

Chat explains intent.
Console shows computation.
Backend remembers results.
Agent interprets only real results.

## Acceptance

No runtime test, no acceptance.

Mock tests are not production acceptance.

Final acceptance requires deployed air-api calling real air-r-service.

Required tests:
1. Guided simulate df: code only, no execution.
2. Autonomous simulate df: real R execution.
3. Autonomous summarize it: same R session.
4. Follow-up interpretation: uses real stored output.
5. Vague objective: shapes statistical question/hypothesis.
