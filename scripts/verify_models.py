import os
from google import genai

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = "us-central1"

def check_model(model_id):
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        # Try a very simple call to verify project has access
        res = client.models.generate_content(
            model=model_id,
            contents="hi"
        )
        print(f"SUCCESS: Project has access to {model_id}")
        return True
    except Exception as e:
        print(f"FAILED: No access to {model_id}. Error: {e}")
        return False

# Check 2.5 Flash and then 1.5 Flash as fallback if needed
if not check_model("gemini-2.5-flash"):
    check_model("gemini-1.5-flash")
