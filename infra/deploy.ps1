# infra/deploy.ps1
$PROJECT_ID = gcloud config get-value project
$REGION = "us-central1"
$BUCKET = "$PROJECT_ID-sessions"

Write-Host "Deploying R Service (Private)..." -ForegroundColor Cyan
gcloud run deploy air-r-service `
  --source ./r-service `
  --no-allow-unauthenticated `
  --region $REGION `
  --memory 2Gi `
  --project $PROJECT_ID `
  --quiet

$R_URL = gcloud run services describe air-r-service --region $REGION --format="value(status.url)"
Write-Host "R Service URL: $R_URL" -ForegroundColor Green

Write-Host "Deploying API Control Plane (Public)..." -ForegroundColor Cyan
gcloud run deploy air-api `
  --source ./api `
  --allow-unauthenticated `
  --region $REGION `
  --project $PROJECT_ID `
  --update-env-vars "R_RUNTIME_URL=$R_URL,SESSION_BUCKET=$BUCKET,DATA_STORE_ID=r-docs-curated,SEARCH_LOCATION=global,GOOGLE_CLOUD_PROJECT=$PROJECT_ID" `
  --quiet

$API_URL = gcloud run services describe air-api --region $REGION --format="value(status.url)"
Write-Host "API URL: $API_URL" -ForegroundColor Green

Write-Host "Deploying Web Frontend (Public)..." -ForegroundColor Cyan
gcloud run deploy air-web `
  --source ./web `
  --allow-unauthenticated `
  --region $REGION `
  --project $PROJECT_ID `
  --set-build-env-vars "NEXT_PUBLIC_API_BASE=https://air-api-652486026072.us-central1.run.app,NEXT_PUBLIC_API_SECRET=$env:NEXT_PUBLIC_API_SECRET" `
  --quiet
