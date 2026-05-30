# PROMPT: "Generate a pytest suite for store operational anomaly detection rules. Write unit tests validating that the anomaly detection engine correctly identifies CAMERA_FAILURE when a camera has been inactive for over 2 minutes, LONG_QUEUE when billing counter occupancy exceeds 5, and FOOTFALL_SPIKE when entry event frequency rises suddenly."
# CHANGES MADE: Integrated in-memory SQLite DB, set custom timestamps representing relative datetime intervals, and validated anomaly output structures.

import pytest
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adjust path to find app package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.db_models import DBEvent
from app.anomalies import detect_anomalies

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()

def test_camera_failure_detection(db_session):
    store_id = "STORE_BLR_002"
    now = datetime.now()

    # Seed one event from Camera-1 (10 seconds ago) and one from Camera-2 (5 minutes ago)
    events = [
        DBEvent(event_id="e1", store_id=store_id, camera_id="Cam-1", visitor_id="v1", event_type="ENTRY", timestamp=now - timedelta(seconds=10), zone_id=None),
        DBEvent(event_id="e2", store_id=store_id, camera_id="Cam-2", visitor_id="v2", event_type="ENTRY", timestamp=now - timedelta(minutes=5), zone_id=None)
    ]
    db_session.add_all(events)
    db_session.commit()

    anomalies = detect_anomalies(db_session, store_id)
    
    # Cam-2 is inactive for > 2 minutes and should trigger CAMERA_FAILURE
    cam_failures = [a for a in anomalies if a["type"] == "CAMERA_FAILURE"]
    assert len(cam_failures) == 1
    assert "Cam-2" in cam_failures[0]["description"]
    assert cam_failures[0]["severity"] == "CRITICAL"

def test_long_queue_detection(db_session):
    store_id = "STORE_BLR_002"
    now = datetime.now()

    # Seed 6 active visitors entering the Billing Counter zone 3 minutes ago with no exit events
    events = []
    for i in range(6):
        visitor_id = f"v_{i}"
        events.append(DBEvent(event_id=f"ent_{i}", store_id=store_id, camera_id="Cam-3", visitor_id=visitor_id, event_type="ZONE_ENTER", zone_id="Billing Counter", timestamp=now - timedelta(minutes=3)))

    db_session.add_all(events)
    db_session.commit()

    anomalies = detect_anomalies(db_session, store_id)
    long_queues = [a for a in anomalies if a["type"] == "LONG_QUEUE"]
    
    # 6 visitors currently in queue (exceeds threshold of 5)
    assert len(long_queues) == 1
    assert "Long queue" in long_queues[0]["description"]
    assert long_queues[0]["severity"] == "WARNING"
