from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db_models import DBEvent
import uuid

def detect_anomalies(db: Session, store_id: str):
    anomalies = []
    now = datetime.now()

    # 1. Camera Failure Detection
    cameras = db.query(DBEvent.camera_id).filter(DBEvent.store_id == store_id).distinct().all()
    for (camera_id,) in cameras:
        latest_event = db.query(DBEvent.timestamp).filter(
            DBEvent.store_id == store_id,
            DBEvent.camera_id == camera_id
        ).order_by(DBEvent.timestamp.desc()).first()

        if latest_event:
            latest_time = latest_event[0]
            if now - latest_time > timedelta(minutes=2):
                anomalies.append({
                    "anomaly_id": str(uuid.uuid4()),
                    "store_id": store_id,
                    "type": "CAMERA_FAILURE",
                    "description": f"Camera '{camera_id}' has not sent events for more than 2 minutes. Last event at {latest_time.strftime('%I:%M:%S %p')}.",
                    "timestamp": now,
                    "severity": "CRITICAL"
                })

    # 2. Long Queue Detection
    billing_entries = db.query(DBEvent.visitor_id, DBEvent.timestamp).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ZONE_ENTER",
        DBEvent.zone_id.like("%Billing%")
    ).all()

    in_queue = set()
    for entry in billing_entries:
        visitor_id, entry_time = entry
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

    avg_prev_5 = entries_prev_55 / 11.0 if entries_prev_55 > 0 else 0.0

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
    if 9 <= now.hour < 21:
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
