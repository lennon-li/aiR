import os
import requests
import subprocess
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleAuthRequest

def normalize_plot_refs(raw_plots, plot_url=None):
    plot_urls = []
    candidates = list(raw_plots or [])
    if plot_url:
        candidates.append(plot_url)

    for raw_path in candidates:
        plot_path = raw_path[0] if isinstance(raw_path, list) and len(raw_path) > 0 else raw_path
        if not isinstance(plot_path, str) or not plot_path:
            continue
        if plot_path.startswith("http://") or plot_path.startswith("https://"):
            plot_urls.append(plot_path)
        else:
            plot_urls.append(f"/v1/artifacts/{plot_path.lstrip('/')}")

    return list(dict.fromkeys(plot_urls))

def normalize_r_service_result(r_result: dict) -> dict:
    normalized = dict(r_result or {})
    normalized.setdefault("status", "success")
    if "stdout" not in normalized:
        normalized["stdout"] = normalized.get("output", "")
    if "environment" not in normalized or normalized["environment"] is None:
        normalized["environment"] = []
    if "objects_changed" not in normalized or normalized["objects_changed"] is None:
        normalized["objects_changed"] = []
    normalized["plots"] = normalize_plot_refs(
        normalized.get("plots", []),
        plot_url=normalized.get("plot_url"),
    )
    return normalized

def get_id_token(url):
    """Retrieves an identity token, falling back to gcloud if needed."""
    try:
        return id_token.fetch_id_token(GoogleAuthRequest(), url)
    except:
        try:
            # Fallback for local development
            return subprocess.check_output(["gcloud", "auth", "print-identity-token", f"--audiences={url}"], text=True).strip()
        except:
            return None

def execute_r_code_internal(code: str, session_id: str) -> dict:
    """
    Backend implementation that calls the R service.
    """
    R_RUNTIME_URL = os.getenv("R_RUNTIME_URL")
    SESSION_BUCKET = os.getenv("SESSION_BUCKET", "air-mvp-lennon-li-2026-sessions")
    
    try:
        token = get_id_token(R_RUNTIME_URL)
        if not token:
            raise ValueError("Could not retrieve identity token for R service.")
            
        r_payload = {"session_id": session_id, "code": code, "persist_bucket": SESSION_BUCKET}
        resp = requests.post(f"{R_RUNTIME_URL}/execute", json=r_payload, headers={"Authorization": f"Bearer {token}"}, timeout=120)
        
        if resp.status_code != 200:
            error_msg = f"R Service Error ({resp.status_code})"
            try:
                error_msg = resp.json().get("error", error_msg)
            except:
                error_msg = f"R Service Failure ({resp.status_code}): {resp.text[:200]}"
            return {"ok": False, "error": error_msg}
            
        r_result = normalize_r_service_result(resp.json())
        if r_result.get("status") == "error":
            return {"ok": False, "error": r_result.get("error"), "stdout": r_result.get("stdout", "")}

        return {
            "ok": True,
            "stdout": r_result.get("stdout", ""),
            "error": None,
            "plots": r_result.get("plots", []),
            "environment": r_result.get("environment", []),
            "objects_changed": r_result.get("objects_changed", [])
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# The tool declaration that the LLM will see
# We only expose the `code` parameter to the LLM.
# The orchestrator will inject the session_id.
execute_r_code_declaration = {
    "name": "execute_r_code",
    "description": "Executes R code in the current aiR session. Used for analysis, plotting, modeling, and calculations. Returns stdout, error (if any), generated plots, and environment summary.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "code": {
                "type": "STRING",
                "description": "Complete, valid R code to execute in the current session environment. Must not include markdown fences."
            }
        },
        "required": ["code"]
    }
}
