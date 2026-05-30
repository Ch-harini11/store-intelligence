import requests
import json

# Target Ingestion URL
INGEST_URL = "http://127.0.0.1:8000/events/ingest"

def post_events(events):
    """
    Transmit generated CV events to the FastAPI Ingest endpoint.
    """
    if not events:
        return

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(INGEST_URL, data=json.dumps(events), headers=headers, timeout=5)
        if response.status_code in [200, 201]:
            print(f"[EMIT] Emitted {len(events)} events to API. Status: {response.status_code}")
            return True
        else:
            print(f"[EMIT ERROR] API responded with code {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[EMIT ERROR] Failed to connect to ingestion server: {str(e)}")
        return False
