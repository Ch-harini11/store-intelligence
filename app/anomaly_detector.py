from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import DBEvent
import uuid

def detect_anomalies(db: Session, store_id: str):
    anomalies = []
    now = datetime.now()

    # 1. Camera Failure Detection
    # Detect if any camera hasn't sent any events in the last 2 minutes, provided there was some activity earlier.
    # First, list all unique cameras that have ever sent events for this store
    cameras = db.query(DBEvent.camera_id).filter(DBEvent.store_id == store_id).distinct().all()
    for (camera_id,) in cameras:
        # Find the latest event from this camera
        latest_event = db.query(DBEvent.timestamp).filter(
            DBEvent.store_id == store_id,
            DBEvent.camera_id == camera_id
        ).order_by(DBEvent.timestamp.desc()).first()

        if latest_event:
            latest_time = latest_event[0]
            # If the difference is greater than 2 minutes
            if now - latest_time > timedelta(minutes=2):
                anomalies.append({
                    "anomaly_id": str(uuid.uuid4()),
                    "store_id": store_id,
                    "type": "CAMERA_FAILURE",
                    "description": f"Camera '{camera_id}' has not sent events for more than 2 minutes. Last event at {latest_time.strftime('%I:%M:%S %p')}.",
                    "timestamp": now,
                    "severity": "CRITICAL"
                })

    # 2. Long Queue Detection at Billing Counter
    # Count the number of visitors who entered the Billing Counter zone in the last 15 minutes and haven't exited
    billing_entries = db.query(DBEvent.visitor_id, DBEvent.timestamp).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ZONE_ENTER",
        DBEvent.zone_id.like("%Billing%")
    ).all()

    # Keep track of who is currently in queue
    in_queue = set()
    for entry in billing_entries:
        visitor_id, entry_time = entry
        # Check if they exited the Billing Counter after this entry
        has_exited = db.query(DBEvent.event_id).filter(
            DBEvent.store_id == store_id,
            DBEvent.visitor_id == visitor_id,
            DBEvent.event_type == "ZONE_EXIT",
            DBEvent.zone_id.like("%Billing%"),
            DBEvent.timestamp > entry_time
        ).first() is not None
        
        if not has_exited:
            in_queue.add(visitor_id)

    if len(in_queue) > 5:
        anomalies.append({
            "anomaly_id": str(uuid.uuid4()),
            "store_id": store_id,
            "type": "LONG_QUEUE",
            "description": f"Long queue detected at Billing Counter. There are {len(in_queue)} visitors currently waiting.",
            "timestamp": now,
            "severity": "WARNING"
        })

    # 3. Sudden Footfall Spike Detection
    # Count entries in last 5 minutes vs average entries per 5 minutes in previous 55 minutes
    five_mins_ago = now - timedelta(minutes=5)
    one_hour_ago = now - timedelta(minutes=60)
    
    entries_last_5 = db.query(DBEvent.event_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ENTRY",
        DBEvent.timestamp >= five_mins_ago
    ).count()

    entries_prev_55 = db.query(DBEvent.event_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ENTRY",
        DBEvent.timestamp >= one_hour_ago,
        DBEvent.timestamp < five_mins_ago
    ).count()

    # Average per 5-minute interval in the previous 55 minutes (11 intervals)
    avg_prev_5 = entries_prev_55 / 11.0 if entries_prev_55 > 0 else 0.0

    # Trigger spike if last 5 mins has >= 5 entries AND is more than 3x the average of previous 5 mins
    if entries_last_5 >= 5 and (avg_prev_5 == 0 or entries_last_5 > 3 * avg_prev_5):
        anomalies.append({
            "anomaly_id": str(uuid.uuid4()),
            "store_id": store_id,
            "type": "FOOTFALL_SPIKE",
            "description": f"Sudden footfall spike detected: {entries_last_5} entries in last 5 minutes (average was {avg_prev_5:.1f} per 5m).",
            "timestamp": now,
            "severity": "WARNING"
        })

    # 4. Empty Store During Business Hours
    # Business hours: 9:00 AM to 9:00 PM (local time)
    # Check if there are no active visitors in the store (entered but not exited)
    if 9 <= now.hour < 21:
        # Check active visitors in the last 30 minutes
        # Total entries in last 30 mins
        recent_entries = db.query(DBEvent.visitor_id).filter(
            DBEvent.store_id == store_id,
            DBEvent.event_type == "ENTRY",
            DBEvent.timestamp >= now - timedelta(minutes=30)
        ).distinct().count()

        if recent_entries == 0:
            anomalies.append({
                "anomaly_id": str(uuid.uuid4()),
                "store_id": store_id,
                "type": "EMPTY_STORE",
                "description": "The store is empty during business hours. No entry events recorded in the last 30 minutes.",
                "timestamp": now,
                "severity": "WARNING"
            })

    return anomalies
