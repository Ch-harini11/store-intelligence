from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db_models import DBEvent

def get_system_health(db: Session):
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_connected = True
    except Exception:
        db_connected = False

    status = "healthy"
    warnings = []
    store_statuses = {}
    now = datetime.utcnow()

    if not db_connected:
        return {
            "status": "unhealthy",
            "database_connected": False,
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stores": {},
            "warnings": ["DATABASE_DISCONNECTED: Unable to establish SQLite session."]
        }

    # Query last event timestamp per store
    stores = db.query(DBEvent.store_id).distinct().all()
    
    for (store_id,) in stores:
        latest_event = db.query(DBEvent.timestamp).filter(
            DBEvent.store_id == store_id
        ).order_by(DBEvent.timestamp.desc()).first()

        if latest_event:
            latest_time = latest_event[0]
            lag_seconds = int((now - latest_time).total_seconds())
            is_stale = lag_seconds > 600  # 10 minutes threshold

            store_statuses[store_id] = {
                "latest_event_timestamp": latest_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "feed_lag_seconds": lag_seconds,
                "feed_status": "STALE" if is_stale else "ACTIVE"
            }

            if is_stale:
                warnings.append(f"STALE_FEED: Store '{store_id}' feed has a lag of {lag_seconds / 60:.1f} minutes.")
                status = "degraded"
        else:
            store_statuses[store_id] = {
                "latest_event_timestamp": None,
                "feed_lag_seconds": None,
                "feed_status": "NO_DATA"
            }

    return {
        "status": status,
        "database_connected": db_connected,
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stores": store_statuses,
        "warnings": warnings
    }
