from fastapi import APIRouter
from typing import List

from app.models import Event

router = APIRouter()

events_db = []

@router.post("/events/ingest")
def ingest(events: List[Event]):
    for event in events:
        events_db.append(event)

    return {
        "accepted": len(events)
    }