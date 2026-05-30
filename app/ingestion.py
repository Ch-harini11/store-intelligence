from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import DBEvent
from app.schemas import EventCreate

router = APIRouter()

@router.post("/events/ingest", status_code=status.HTTP_201_CREATED)
def ingest_events(events: List[EventCreate], db: Session = Depends(get_db)):
    if not events:
        return {"accepted": 0, "skipped": 0}

    # Extract all event IDs from the batch
    event_ids = [e.event_id for e in events]

    # Query for existing event IDs in the database for deduplication
    existing_records = db.query(DBEvent.event_id).filter(DBEvent.event_id.in_(event_ids)).all()
    existing_ids = {r[0] for r in existing_records}

    new_events = []
    skipped_count = 0

    for event_data in events:
        if event_data.event_id in existing_ids:
            skipped_count += 1
            continue

        db_event = DBEvent(
            event_id=event_data.event_id,
            store_id=event_data.store_id,
            camera_id=event_data.camera_id,
            visitor_id=event_data.visitor_id,
            event_type=event_data.event_type,
            timestamp=event_data.timestamp,
            zone_id=event_data.zone_id,
            dwell_ms=event_data.dwell_ms,
            is_staff=event_data.is_staff,
            confidence=event_data.confidence,
            metadata=event_data.metadata
        )
        new_events.append(db_event)

    if new_events:
        db.add_all(new_events)
        db.commit()

    return {
        "accepted": len(new_events),
        "skipped": skipped_count
    }