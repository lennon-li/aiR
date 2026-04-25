# scripts/verify_vertical_slice.ps1
# End-to-end verification of the aiR vertical slice (API -> R Service)

$PROJECT_ID = "air-mvp-lennon-li-2026"
$API_URL = "https://air-api-43va3skqta-uc.a.run.app"

Write-Host "--- 1. Authenticating ---" -ForegroundColor Cyan
$token = (gcloud auth print-identity-token)
if (-not $token) { 
    Write-Error "Failed to get identity token. Are you logged in?"
    exit 1
}

Write-Host "--- 2. Creating Session ---" -ForegroundColor Cyan
$session_payload = @{
    objective = "Vertical Slice Verification"
    slider_value = 20
} | ConvertTo-Json

try {
    $session = Invoke-RestMethod -Uri "$API_URL/v1/sessions" -Method Post -Body $session_payload -ContentType "application/json" -Headers @{Authorization="Bearer $token"}
    $session_id = $session.session_id
    Write-Host "Session Created: $session_id" -ForegroundColor Green
} catch {
    Write-Error "Failed to create session: $_"
    exit 1
}

Write-Host "--- 3. Executing R Code ---" -ForegroundColor Cyan
# This code generates stdout, a plot, and an environment variable
$execute_payload = @{
    code = "set.seed(123); data_vec <- rnorm(10); mean(data_vec); plot(data_vec)"
    provenance = "Regression Test"
    is_agent_code = $false
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "$API_URL/v1/sessions/$session_id/execute" -Method Post -Body $execute_payload -ContentType "application/json" -Headers @{Authorization="Bearer $token"}
    
    $passed = $true
    
    # 3a. Verify Status
    if ($result.status -contains "success") {
        Write-Host "[PASS] Status is success" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Status is not success: $($result.status)" -ForegroundColor Red
        $passed = $false
    }
    
    # 3b. Verify Stdout
    if ($result.stdout -match "0\.07462564") {
        Write-Host "[PASS] Console output contains expected calculation" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Console output missing or incorrect: $($result.stdout)" -ForegroundColor Red
        $passed = $false
    }
    
    # 3c. Verify Plots
    if ($result.plots.Count -ge 1) {
        Write-Host "[PASS] Plot artifact generated: $($result.plots[0])" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] No plot artifact returned" -ForegroundColor Red
        $passed = $false
    }
    
    # 3d. Verify Environment
    $env_found = $false
    foreach ($obj in $result.environment) {
        if ($obj.name -contains "data_vec") {
            $env_found = $true
            Write-Host "[PASS] Environment contains 'data_vec' ($($obj.type))" -ForegroundColor Green
        }
    }
    if (-not $env_found) {
        Write-Host "[FAIL] 'data_vec' not found in environment" -ForegroundColor Red
        $passed = $false
    }
    
    if ($passed) {
        Write-Host "--- VERTICAL SLICE VERIFIED ---" -ForegroundColor Black -BackgroundColor Green
    } else {
        Write-Host "--- VERIFICATION FAILED ---" -ForegroundColor White -BackgroundColor Red
        exit 1
    }

} catch {
    Write-Error "Execution failed: $_"
    exit 1
}
