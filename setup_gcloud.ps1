# setup_gcloud.ps1
$PROJECT_ID = "air-mvp-lennon-li-2026"
$LOCATION = "global"

Write-Host "Setting Vertex AI environment variables for User scope..." -ForegroundColor Cyan

# Set environment variables at the User level so they persist across sessions
[Environment]::SetEnvironmentVariable("GOOGLE_CLOUD_PROJECT", $PROJECT_ID, "User")
[Environment]::SetEnvironmentVariable("GOOGLE_CLOUD_LOCATION", $LOCATION, "User")
[Environment]::SetEnvironmentVariable("GOOGLE_GENAI_USE_VERTEXAI", "true", "User")

# Set for current session as well
$env:GOOGLE_CLOUD_PROJECT = $PROJECT_ID
$env:GOOGLE_CLOUD_LOCATION = $LOCATION
$env:GOOGLE_GENAI_USE_VERTEXAI = "true"

Write-Host "Successfully set GOOGLE_CLOUD_PROJECT to $PROJECT_ID" -ForegroundColor Green
Write-Host "Successfully set GOOGLE_CLOUD_LOCATION to $LOCATION" -ForegroundColor Green
Write-Host "Successfully set GOOGLE_GENAI_USE_VERTEXAI to true" -ForegroundColor Green

Write-Host "`nSetting gcloud project..." -ForegroundColor Cyan
gcloud config set project $PROJECT_ID

Write-Host "`nNote: If you haven't authenticated recently, you may need to run:" -ForegroundColor Yellow
Write-Host "gcloud auth application-default login" -ForegroundColor White
Write-Host "`nNote: You may need to restart your terminal or Gemini CLI for these changes to take full effect." -ForegroundColor Yellow
