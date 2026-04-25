# scripts/vertex_login.ps1
Write-Host "Fetching your Google Cloud projects..." -ForegroundColor Cyan
$projects = gcloud projects list --format="value(projectId)"

if ($null -eq $projects -or $projects.Count -eq 0) {
    Write-Host "No projects found or you are not logged in to gcloud." -ForegroundColor Red
    exit 1
}

Write-Host "`n--- Available Projects ---" -ForegroundColor Green
gcloud projects list --format="table(projectId, name)"

$projectId = Read-Host "`nEnter the Project ID you want to use"

if (-not $projectId) {
    Write-Host "No project ID provided. Aborted." -ForegroundColor Red
    exit 1
}

Write-Host "`nConfiguring $projectId..." -ForegroundColor Cyan
gcloud config set project $projectId
gcloud auth application-default login
gcloud auth application-default set-quota-project $projectId

# Persist environment variables for future sessions
[Environment]::SetEnvironmentVariable("GOOGLE_CLOUD_PROJECT", $projectId, "User")
[Environment]::SetEnvironmentVariable("GOOGLE_CLOUD_LOCATION", "global", "User")
[Environment]::SetEnvironmentVariable("GOOGLE_GENAI_USE_VERTEXAI", "true", "User")

Write-Host "`nSuccessfully configured Vertex AI login for project: $projectId" -ForegroundColor Green
