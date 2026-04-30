# aiR Agent Workflow

## Working rule

Research -> Strategy -> Execution -> Verification -> Handoff

## Before changing code

1. Identify OS/shell.
2. Identify target service/file.
3. Read current architecture docs.
4. Check whether change affects:
   - frontend,
   - air-api,
   - air-r-service,
   - Conversation Agent,
   - GCS persistence,
   - Cloud Run deployment.

## During implementation

1. Use PowerShell commands.
2. Exclude generated folders from searches.
3. Make small changes.
4. Do not reintroduce df-messenger.
5. Preserve mode behavior.
6. Preserve anti-hallucination rules.
7. Preserve session-scoped GCS persistence.

## Before handoff

Must report:
1. Files changed.
2. Tests run.
3. Whether tests were mock or real.
4. Whether deployed Cloud Run path was tested.
5. Whether real R execution passed.
6. Whether GCS persistence passed.
7. Remaining risks.

## Handoff format

Use the required format from AGENTS.md.
If AGENTS.md is not present or does not define a format, use the format established in the project history.
