# api/telemetry.py
import json
import time
import sys
from datetime import datetime

def log_event(event_type: str, session_id: str = None, data: dict = None):
    """
    Emits a structured JSON log for Cloud Logging.
    """
    try:
        payload = {
            "severity": "INFO",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": f"Telemetry: {event_type}",
            "event_type": event_type,
            "session_id": session_id,
            "payload": data or {}
        }
        # Print to stdout for Cloud Run collection
        print(json.dumps(payload))
        sys.stdout.flush()
    except:
        pass

class TelemetryTimer:
    def __init__(self):
        self.start = time.time()
        self.duration_ms = 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.duration_ms = int((time.time() - self.start) * 1000)
