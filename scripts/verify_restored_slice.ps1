# scripts/verify_restored_slice.ps1
$token = (gcloud auth print-identity-token)
$api_url = "https://air-api-43va3skqta-uc.a.run.app"

function Test-Command($sid, $code, $expected_regex) {
    Write-Host "Executing: $code" -ForegroundColor Cyan
    $body = @{code=$code} | ConvertTo-Json
    $headers = @{Authorization="Bearer $token"}
    $res = Invoke-RestMethod -Uri "$api_url/v1/sessions/$sid/execute" -Method Post -Body $body -ContentType "application/json" -Headers $headers
    
    $stdout = ""
    if ($null -ne $res.stdout) {
        $stdout = $res.stdout.Trim()
    }

    if ($stdout -match $expected_regex) {
        Write-Host "PASS: Output matches expected" -ForegroundColor Green
        return $res
    } else {
        Write-Host "FAIL: Output mismatch. Got: '$stdout', Expected Regex: '$expected_regex'" -ForegroundColor Red
        return $null
    }
}

Write-Host "--- 1. Creating Session ---"
$session_body = @{objective="Restoration Verification"; slider_value=20} | ConvertTo-Json
$session = Invoke-RestMethod -Uri "$api_url/v1/sessions" -Method Post -Body $session_body -ContentType "application/json" -Headers @{Authorization="Bearer $token"}
$sid = $session.session_id
Write-Host "Session ID: $sid"

Write-Host "--- 2. Verify Single Output for print(10) ---"
$res = Test-Command $sid "print(10)" "^\[1\] 10$"
if ($null -eq $res) { exit 1 }

Write-Host "--- 3. Verify Analyst Packages (ggplot2, dplyr) ---"
$code_packages = "library(ggplot2); library(dplyr); iris %>% group_by(Species) %>% summarize(m=mean(Sepal.Length)) %>% pull(m) %>% first()"
$res = Test-Command $sid $code_packages "5\.006"
if ($null -eq $res) { exit 1 }

Write-Host "--- 4. Verify Plot Generation ---"
$plot_body = @{code="library(ggplot2); print(ggplot(iris, aes(x=Species, y=Petal.Length)) + geom_boxplot())"} | ConvertTo-Json
$res = Invoke-RestMethod -Uri "$api_url/v1/sessions/$sid/execute" -Method Post -Body $plot_body -ContentType "application/json" -Headers @{Authorization="Bearer $token"}
if ($res.plots.Count -ge 1) {
    Write-Host "PASS: Plot generated" -ForegroundColor Green
} else {
    Write-Host "FAIL: No plot generated" -ForegroundColor Red
    Write-Host "Response was: $($res | ConvertTo-Json -Depth 5)"
    exit 1
}

Write-Host "--- 5. Verify Persistence (x <- 42) ---"
$persist_body = @{code="x <- 42"} | ConvertTo-Json
Invoke-RestMethod -Uri "$api_url/v1/sessions/$sid/execute" -Method Post -Body $persist_body -ContentType "application/json" -Headers @{Authorization="Bearer $token"} | Out-Null
$res = Test-Command $sid "print(x)" "^\[1\] 42$"
if ($null -eq $res) { exit 1 }

Write-Host "--- 6. Verify Copilot Code No Fences ---"
$chat_body = @{message="write R code to sum 1 to 10"; slider_value=20} | ConvertTo-Json
$chat_res = Invoke-RestMethod -Uri "$api_url/v1/sessions/$sid/chat" -Method Post -Body $chat_body -ContentType "application/json" -Headers @{Authorization="Bearer $token"}
$response_text = $chat_res.response
if ($response_text.Contains('```')) {
    Write-Host "FAIL: Copilot output contains markdown fences" -ForegroundColor Red
    Write-Host "Response: $response_text"
    exit 1
} else {
    Write-Host "PASS: Copilot output is raw R code" -ForegroundColor Green
}

Write-Host "--- VERTICAL SLICE FULLY RESTORED ---" -ForegroundColor Black -BackgroundColor Green
