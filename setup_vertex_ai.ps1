# Setup script for AI Your Book Vertex AI Session
$PROJECT_ID = "air-mvp-lennon-li-2026"
$LOCATION = "global"

# Set Environment Variables for the current session
$env:GOOGLE_CLOUD_PROJECT = $PROJECT_ID
$env:GOOGLE_CLOUD_LOCATION = $LOCATION
$env:GOOGLE_GENAI_USE_VERTEXAI = "true"

Write-Host "--- Vertex AI Session Prep ---" -ForegroundColor Cyan
Write-Host "Setting gcloud project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

Write-Host "`nEnvironment Variables Set:" -ForegroundColor Green
Write-Host "GOOGLE_CLOUD_PROJECT: $env:GOOGLE_CLOUD_PROJECT"
Write-Host "GOOGLE_CLOUD_LOCATION: $env:GOOGLE_CLOUD_LOCATION"
Write-Host "GOOGLE_GENAI_USE_VERTEXAI: $env:GOOGLE_GENAI_USE_VERTEXAI"

Write-Host "`nIf you haven't authenticated recently, please run:" -ForegroundColor Yellow
Write-Host "gcloud auth application-default login" -ForegroundColor White
Write-Host "----------------------------"
