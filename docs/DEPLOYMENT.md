# aiR Deployment Process

## Default environment

OS/shell:
Windows PowerShell

Do not use bash/Linux commands unless explicitly told.

## Services

Project:
air-mvp-lennon-li-2026

Region:
us-central1

Services:
- air-web
- air-api
- air-r-service
- air-r-backend legacy/old

## Check services

gcloud run services list --platform=managed --region=us-central1

## Check service URLs

gcloud run services describe air-web `
  --region=us-central1 `
  --format="value(status.url)"

gcloud run services describe air-api `
  --region=us-central1 `
  --format="value(status.url)"

gcloud run services describe air-r-service `
  --region=us-central1 `
  --format="value(status.url)"

## Check air-api env vars

gcloud run services describe air-api `
  --region=us-central1 `
  --format="yaml(spec.template.spec.containers[0].env)"

Required/important env vars:
- GOOGLE_CLOUD_PROJECT=air-mvp-lennon-li-2026
- GOOGLE_CLOUD_LOCATION=global
- CONVERSATION_AGENT_ID=1e9ad1e9-30bb-45ad-98e1-16714da84164
- CONVERSATION_AGENT_LANGUAGE_CODE=en
- R_RUNTIME_URL or R_SERVICE_URL pointing to air-r-service
- GCS/session bucket setting
- no production MOCK execution flag

## Check frontend env vars

gcloud run services describe air-web `
  --region=us-central1 `
  --format="yaml(spec.template.spec.containers[0].env)"

Important:
air-web should call air-api, not air-r-service directly.

## Deploy principle

Do not treat local mock verification as production acceptance.

Final acceptance requires deployed air-api to call deployed air-r-service and execute real R code.

## Deployment checklist

Before deployment:
1. Confirm tests pass locally where possible.
2. Confirm no broad search over node_modules or generated folders.
3. Confirm no df-messenger widget is reintroduced.
4. Confirm air-api points to air-r-service, not air-r-backend.
5. Confirm MOCK execution is disabled for production.

After deployment:
1. Test /v1/agent/chat in guided mode.
2. Test /v1/agent/chat in autonomous mode.
3. Confirm real R execution.
4. Confirm GCS persistence.
5. Confirm follow-up interpretation uses real stored output.
6. Confirm browser behavior at air.biostats.ca.
