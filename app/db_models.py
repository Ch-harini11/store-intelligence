from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON
from app.database import Base

class DBEvent(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, index=True, nullable=False)
    camera_id = Column(String, nullable=False)
    visitor_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)  # ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, DWELL, PURCHASE
    timestamp = Column(DateTime, nullable=False)
    zone_id = Column(String, nullable=True)
    dwell_ms = Column(Integer, default=0)
    is_staff = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)
    event_metadata = Column("metadata", JSON, nullable=True)
