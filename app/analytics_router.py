from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app.models import DBEvent
from app.schemas import StoreMetrics, ConversionFunnel, Anomaly
from app.anomaly_detector import detect_anomalies

router = APIRouter()

@router.get("/stores/{store_id}/metrics", response_model=StoreMetrics)
def get_store_metrics(store_id: str, db: Session = Depends(get_db)):
    # 1. Footfall: Unique visitor entries
    footfall = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ENTRY"
    ).distinct().count()

    # 2. Unique visitors overall
    unique_visitors = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id
    ).distinct().count()

    # Fallback if ENTRY events are not explicitly generated
    if footfall == 0 and unique_visitors > 0:
        footfall = unique_visitors

    # 3. Average Dwell Time: average of dwell_ms for DWELL/EXIT events (where dwell_ms > 0)
    avg_dwell = db.query(func.avg(DBEvent.dwell_ms)).filter(
        DBEvent.store_id == store_id,
        DBEvent.dwell_ms > 0
    ).scalar()
    
    avg_dwell_time_ms = float(avg_dwell) if avg_dwell is not None else 0.0

    # 4. Peak Hour: Hour with the most ENTRY events
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
        # Fallback to general event counts if no ENTRY events
        peak_hour_query = db.query(
            func.strftime('%H', DBEvent.timestamp).label('hour'),
            func.count(DBEvent.event_id).label('cnt')
        ).filter(
            DBEvent.store_id == store_id
        ).group_by('hour').order_by(func.count(DBEvent.event_id).desc()).first()
        peak_hour = int(peak_hour_query[0]) if peak_hour_query else 12

    return StoreMetrics(
        store_id=store_id,
        footfall=footfall,
        unique_visitors=unique_visitors,
        avg_dwell_time_ms=avg_dwell_time_ms,
        peak_hour=peak_hour
    )

@router.get("/stores/{store_id}/funnel", response_model=ConversionFunnel)
def get_conversion_funnel(store_id: str, db: Session = Depends(get_db)):
    # Visitors Entered (ENTRY events)
    visitors_entered = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        DBEvent.event_type == "ENTRY"
    ).distinct().count()

    # Fallback to unique visitors overall if 0
    if visitors_entered == 0:
        visitors_entered = db.query(DBEvent.visitor_id).filter(
            DBEvent.store_id == store_id
        ).distinct().count()

    # Visitors Visited Shelf (visited 'Shelf A' or 'Shelf B' or matching shelf%)
    visitors_visited_shelf = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        (DBEvent.zone_id.like('%Shelf%') | DBEvent.zone_id.like('%shelf%'))
    ).distinct().count()

    # Visitors Billed (entered 'Billing Counter' or had PURCHASE event)
    visitors_billed = db.query(DBEvent.visitor_id).filter(
        DBEvent.store_id == store_id,
        (DBEvent.event_type == "PURCHASE") | (DBEvent.zone_id.like('%Billing%')) | (DBEvent.zone_id.like('%billing%'))
    ).distinct().count()

    # Logical validation: ensure counts follow funnel constraints for visual correctness
    if visitors_visited_shelf > visitors_entered:
        visitors_visited_shelf = visitors_entered
    if visitors_billed > visitors_visited_shelf:
        visitors_billed = visitors_visited_shelf

    conversion_rate = 0.0
    if visitors_entered > 0:
        conversion_rate = round((visitors_billed / visitors_entered) * 100.0, 2)

    return ConversionFunnel(
        store_id=store_id,
        visitors_entered=visitors_entered,
        visitors_visited_shelf=visitors_visited_shelf,
        visitors_billed=visitors_billed,
        conversion_rate=conversion_rate
    )

@router.get("/stores/{store_id}/anomalies", response_model=List[Anomaly])
def get_store_anomalies(store_id: str, db: Session = Depends(get_db)):
    return detect_anomalies(db, store_id)

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Check database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}"
        )

@router.post("/simulation/reset")
def reset_database(db: Session = Depends(get_db)):
    try:
        db.query(DBEvent).delete()
        db.commit()
        return {"status": "success", "message": "Database cleared successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from app.mock_generator import generate_mock_data

@router.post("/simulation/mock")
def seed_mock_data(store_id: str = "store_001", db: Session = Depends(get_db)):
    try:
        inserted = generate_mock_data(db, store_id=store_id)
        return {
            "status": "success", 
            "message": f"Seeded {inserted} mock events for store {store_id}."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate mock data: {str(e)}"
        )

@router.get("/stores/{store_id}/occupancy")
def get_zone_occupancy(store_id: str, db: Session = Depends(get_db)):
    # Get the latest event for each visitor in the store
    subquery = db.query(
        DBEvent.visitor_id,
        func.max(DBEvent.timestamp).label("max_ts")
    ).filter(DBEvent.store_id == store_id).group_by(DBEvent.visitor_id).subquery()
    
    latest_events = db.query(DBEvent).join(
        subquery,
        (DBEvent.visitor_id == subquery.c.visitor_id) & (DBEvent.timestamp == subquery.c.max_ts)
    ).all()

    counts = {
        "Entrance": 0,
        "Shelf A": 0,
        "Shelf B": 0,
        "Billing Counter": 0,
        "Exit": 0
    }

    active_shoppers = 0
    for event in latest_events:
        # If they haven't exited the store yet, determine their current zone
        if event.event_type != "EXIT":
            active_shoppers += 1
            if event.event_type in ["ZONE_ENTER", "ENTRY"]:
                zone = event.zone_id
                if zone in counts:
                    counts[zone] += 1
                elif event.event_type == "ENTRY":
                    counts["Entrance"] += 1
            elif event.event_type == "ZONE_EXIT":
                # If they exited a shelf but haven't entered another zone,
                # they are technically wandering in the main floor or entrance area
                counts["Entrance"] += 1

    return {
        "active_total": active_shoppers,
        "zones": counts
    }


