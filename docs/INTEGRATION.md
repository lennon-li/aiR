# aiR Integration & Deployment Guide

## Production URLs (Deployed April 2026)
- **Web UI:** `https://air-web-652486026072.us-central1.run.app`
- **API (Control Plane):** `https://air-api-652486026072.us-central1.run.app`
- **R Execution Service:** `https://air-r-service-43va3skqta-uc.a.run.app`

## Required Environment Variables

### air-api
- `GOOGLE_CLOUD_PROJECT`: GCP Project ID.
- `R_RUNTIME_URL`: The URL of the `air-r-service`.
- `SESSION_BUCKET`: GCS bucket for session state and artifacts.
- `API_SECRET`: Secret for signing session tokens.
- `DATA_STORE_ID`: Vertex AI Search Data Store ID (for grounding).

### air-web
- `NEXT_PUBLIC_API_BASE`: The URL of the `air-api`.

## Deployment Order
1. **R Execution Service (`air-r-service`)**: Deploy first to obtain its URL.
2. **API (`air-api`)**: Deploy next, configuring `R_RUNTIME_URL` with the R service URL.
3. **Web UI (`air-web`)**: Deploy last, configuring `NEXT_PUBLIC_API_BASE` with the API URL.

## Smoke Test Steps
To verify the vertical slice (Frontend -> API -> R Service), follow these steps:

### Automated Script
Run the regression test script from the project root:
```powershell
powershell.exe -File scripts/verify_vertical_slice.ps1
```

### Manual Verification
1. Open the **Web UI** URL.
2. Enter an objective (e.g., "Verification") and click **START SESSION**.
3. In the console or repl, type: `x <- 1:10; mean(x); plot(x)` and press Enter.
4. **Verify Console:** Output should show `[1] 5.5`.
5. **Verify Plots Tab:** A plot should appear in the right-hand panel.
6. **Verify Environment Tab:** The variable `x` should be listed with its type and details.
