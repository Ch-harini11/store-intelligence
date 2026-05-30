from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class EventBase(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = {}

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    class Config:
        from_attributes = True

class StoreMetrics(BaseModel):
    store_id: str
    footfall: int
    unique_visitors: int
    avg_dwell_time_ms: float
    peak_hour: int

class ConversionFunnel(BaseModel):
    store_id: str
    visitors_entered: int
    visitors_visited_shelf: int
    visitors_billed: int
    conversion_rate: float

class Anomaly(BaseModel):
    anomaly_id: str
    store_id: str
    type: str
    description: str
    timestamp: datetime
    severity: str