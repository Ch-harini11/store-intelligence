from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app.db_models import DBEvent
from app.models import StoreMetrics, ConversionFunnel, Anomaly
from app.anomalies import detect_anomalies
from app.metrics import get_store_metrics_data
from app.funnel import get_conversion_funnel_data
from app.health import get_system_health

router = APIRouter()

@router.get("/stores/{store_id}/metrics", response_model=StoreMetrics)
def get_store_metrics(store_id: str, db: Session = Depends(get_db)):
    try:
        metrics = get_store_metrics_data(store_id, db)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate metrics: {str(e)}"
        )

@router.get("/stores/{store_id}/funnel", response_model=ConversionFunnel)
def get_conversion_funnel(store_id: str, db: Session = Depends(get_db)):
    try:
        funnel = get_conversion_funnel_data(store_id, db)
        return funnel
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate funnel: {str(e)}"
        )

@router.get("/stores/{store_id}/anomalies", response_model=List[Anomaly])
def get_store_anomalies(store_id: str, db: Session = Depends(get_db)):
    try:
        return detect_anomalies(db, store_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan anomalies: {str(e)}"
        )

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        return get_system_health(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
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
        if event.event_type != "EXIT":
            active_shoppers += 1
            if event.event_type in ["ZONE_ENTER", "ENTRY"]:
                zone = event.zone_id
                if zone in counts:
                    counts[zone] += 1
                elif event.event_type == "ENTRY":
                    counts["Entrance"] += 1
            elif event.event_type == "ZONE_EXIT":
                counts["Entrance"] += 1

    return {
        "active_total": active_shoppers,
        "zones": counts
    }
