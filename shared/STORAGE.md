# Cloud Storage Path Conventions

Root Bucket: `gs://{PROJECT_ID}-sessions/`

## Layout
- `/sessions/{session_id}/snapshots/state.RData`  # Binary workspace state
- `/sessions/{session_id}/uploads/{filename}`     # User-uploaded source files
- `/sessions/{session_id}/artifacts/plot_{ts}.png` # Generated visualizations
- `/sessions/{session_id}/exports/{filename}.R`   # Exported scripts/reports

## Access Policy
- Public Access: **Disabled**
- Access Method: **Signed URLs (V4)** issued by the Control Plane.
- Expiration: **15 minutes**.
