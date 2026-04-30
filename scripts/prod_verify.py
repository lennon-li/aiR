import requests
import json
import base64
import subprocess
import sys

API_URL = "http://127.0.0.1:8000"

def get_uuid(sid):
    payload_b64 = sid.split(".")[0]
    missing_padding = len(payload_b64) % 4
    if missing_padding:
        payload_b64 += '=' * (4 - missing_padding)
    data = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
    return data["id"]

def run_test():
    # 1. Create Session
    print("Step 1: Creating Session...")
    resp = requests.post(f"{API_URL}/v1/sessions", json={
        "objective": "production verification real",
        "analysis_mode": "autonomous"
    })
    sid = resp.json()["session_id"]
    uuid = get_uuid(sid)
    print(f"Session Created. UUID: {uuid}")

    # 2. Warm up
    print("\nStep 2: Warming up Dialogflow...")
    warmup_payload = {
        "session_id": sid,
        "message": "hi",
        "context": {
            "guidance_depth": "autonomous",
            "objective": "verification",
            "dataset_summary": "none"
        }
    }
    requests.post(f"{API_URL}/v1/agent/chat", json=warmup_payload)

    # 3. Autonomous Create DF
    print("\nStep 3: Testing autonomous create df...")
    payload = {
        "session_id": sid,
        "message": "I am in autonomous mode. Simulate a dataframe with 3 columns and 10 rows. Assign it to `df`. Wrap your R code in fences.",
        "context": {
            "guidance_depth": "autonomous",
            "objective": "verification",
            "dataset_summary": "none"
        }
    }
    res1 = requests.post(f"{API_URL}/v1/agent/chat", json=payload).json()
    print("Response 1:")
    print(json.dumps(res1, indent=2))

    if not res1.get("executed"):
        print("FAILED: Code was not executed.")
        return

    # 3. Autonomous Summarize
    print("\nStep 3: Testing autonomous summarize...")
    payload["message"] = "summarize it"
    res2 = requests.post(f"{API_URL}/v1/agent/chat", json=payload).json()
    print("Response 2:")
    print(json.dumps(res2, indent=2))

    # 4. Interpretation
    print("\nStep 4: Testing interpretation...")
    payload["message"] = "what does it mean?"
    res3 = requests.post(f"{API_URL}/v1/agent/chat", json=payload).json()
    print("Response 3:")
    print(json.dumps(res3, indent=2))

    # 5. GCS Check
    print("\nStep 5: Checking GCS Persistence...")
    bucket = "air-mvp-lennon-li-2026-sessions"
    gcs_path = f"gs://{bucket}/sessions/{uuid}/last_execution.json"
    print(f"Checking {gcs_path}")
    
    try:
        # Use gsutil as recommended by project patterns
        stat = subprocess.run(["gsutil", "stat", gcs_path], capture_output=True, text=True)
        if stat.returncode == 0:
            print("SUCCESS: last_execution.json found in GCS.")
            content = subprocess.run(["gsutil", "cat", gcs_path], capture_output=True, text=True).stdout
            data = json.loads(content)
            print("GCS Content (Keys):", data.keys())
            print("GCS STDOUT Sample:", data.get("stdout", "")[:100])
        else:
            print(f"FAILURE: GCS object not found. {stat.stderr}")
    except Exception as e:
        print(f"ERROR checking GCS: {e}")

if __name__ == "__main__":
    run_test()
