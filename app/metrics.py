from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db_models import DBEvent

def get_store_metrics_data(store_id: str, db: Session):
    # 1. Footfall: Unique visitor entries
    footfall = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ENTRY"
    ).distinct().count()

    # 2. Unique visitors overall
    unique_visitors = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id
    ).distinct().count()

    if footfall == 0 and unique_visitors > 0:
        footfall = unique_visitors

    # 3. Average Dwell Time
    avg_dwell = db.query(func.avg(DBEvent.dwell_ms)).filter(
        DBEvent.store_id == store_id,
        DBEvent.dwell_ms > 0
    ).scalar()
    
    avg_dwell_time_ms = float(avg_dwell) if avg_dwell is not None else 0.0

    # 4. Peak Hour
    peak_hour_query = db.query(
        func.strftime('%H', DBEvent.timestamp).label('hour'),
        func.count(DBEvent.event_id).label('cnt')
    ).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ENTRY"
    ).group_by('hour').order_by(func.count(DBEvent.event_id).desc()).first()

    if peak_hour_query:
        peak_hour = int(peak_hour_query[0])
    else:
        peak_hour_query = db.query(
            func.strftime('%H', DBEvent.timestamp).label('hour'),
            func.count(DBEvent.event_id).label('cnt')
        ).filter(
            DBEvent.store_id == store_id
        ).group_by('hour').order_by(func.count(DBEvent.event_id).desc()).first()
        peak_hour = int(peak_hour_query[0]) if peak_hour_query else 12

    return {
        "store_id": store_id,
        "footfall": footfall,
        "unique_visitors": unique_visitors,
        "avg_dwell_time_ms": avg_dwell_time_ms,
        "peak_hour": peak_hour
    }
