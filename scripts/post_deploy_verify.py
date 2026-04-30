import requests
import json
import time

API_URL = "https://air-api-43va3skqta-uc.a.run.app"

def verify_prompt(prompt, session_id):
    print(f"\nPROMPT: {prompt}")
    payload = {
        "message": prompt,
        "history": [],
        "env_summary": [],
        "recent_history": []
    }
    
    start = time.time()
    resp = requests.post(f"{API_URL}/v1/sessions/{session_id}/chat", json=payload)
    latency = int((time.time() - start) * 1000)
    
    if resp.status_code == 200:
        data = resp.json()
        is_grounded = data.get("grounded", False)
        g_type = data.get("g_type", "none")
        summary = data.get("response", "")
        print(f"  GROUNDED: {is_grounded} ({g_type})")
        print(f"  LATENCY: {latency}ms")
        print(f"  SUMMARY: {summary[:100]}...")
        return {"grounded": is_grounded, "g_type": g_type, "quality": "ok" if len(summary) > 20 else "poor"}
    else:
        print(f"  ERROR: {resp.status_code} - {resp.text}")
        return None

# 1. Create Session
init_resp = requests.post(f"{API_URL}/v1/sessions", json={"objective": "Verification Suite"})
session_id = init_resp.json()["session_id"]
print(f"Session Created: {session_id}")

positive_prompts = [
    "How do I use pivot_longer in tidyr?",
    "What's the difference between summarise and reframe?",
    "How should I name functions and files in R?",
    "How can I make this R code more readable?",
    "How do I do grouped operations with .SD in data.table?"
]

negative_prompts = [
    "Generate some sample data to work with",
    "Create a mock dataset with 3 columns",
    "Fit a regression on df",
    "Plot mpg against hp",
    "Summarize the dataframe"
]

print("--- TESTING GROUNDING-POSITIVE PROMPTS ---")
for p in positive_prompts:
    verify_prompt(p, session_id)

print("\n--- TESTING GROUNDING-NEGATIVE PROMPTS ---")
for p in negative_prompts:
    verify_prompt(p, session_id)
