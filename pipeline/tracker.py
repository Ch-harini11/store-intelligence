import cv2
import numpy as np
from datetime import datetime, timedelta
import uuid
import random

# Define store layout zones (pixels in 800x600 coordinate system)
ZONES = {
    "Entrance": np.array([[50, 50], [250, 50], [250, 150], [50, 150]], dtype=np.int32),
    "Shelf A": np.array([[50, 220], [350, 220], [350, 350], [50, 350]], dtype=np.int32),
    "Shelf B": np.array([[450, 220], [750, 220], [750, 350], [450, 350]], dtype=np.int32),
    "Billing Counter": np.array([[50, 420], [350, 420], [350, 550], [50, 550]], dtype=np.int32),
    "Exit": np.array([[550, 420], [750, 420], [750, 550], [550, 550]], dtype=np.int32)
}

# Color mapping for drawing
ZONE_COLORS = {
    "Entrance": (0, 255, 0),        # Green
    "Shelf A": (255, 128, 0),       # Orange
    "Shelf B": (255, 0, 128),       # Purple
    "Billing Counter": (0, 255, 255), # Yellow
    "Exit": (0, 0, 255)            # Red
}

def is_point_in_polygon(point, polygon):
    """
    Checks if a 2D point lies inside a spatial polygon.
    """
    result = cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False)
    return result >= 0

class VisitorStateTracker:
    def __init__(self, visitor_id, store_id="STORE_BLR_002", camera_id="CAM_ENTRY_01"):
        self.visitor_id = visitor_id
        self.store_id = store_id
        self.camera_id = camera_id
        self.current_zone = None
        self.zone_entry_time = None
        self.in_store = False
        self.has_billed = False
        self.session_seq = 0

    def update_position(self, point, timestamp=None):
        if not timestamp:
            timestamp = datetime.utcnow() # Use UTC standard for event streams

        # Determine which polygon zone matches the visitor coordinate
        new_zone = None
        for zone_name, polygon in ZONES.items():
            if is_point_in_polygon(point, polygon):
                new_zone = zone_name
                break

        events = []

        # State transition analysis
        if new_zone != self.current_zone:
            # 1. ZONE_EXIT
            if self.current_zone:
                dwell_time_ms = int((timestamp - self.zone_entry_time).total_seconds() * 1000)
                self.session_seq += 1
                
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": self.visitor_id,
                    "event_type": "ZONE_EXIT",
                    "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "zone_id": self.current_zone,
                    "dwell_ms": dwell_time_ms,
                    "is_staff": False,
                    "confidence": 0.95,
                    "metadata": {
                        "sku_zone": self.current_zone,
                        "session_seq": self.session_seq
                    }
                })

                # ZONE_DWELL: if they continuously dwelled in the zone for 30+ seconds
                if dwell_time_ms >= 30000:
                    self.session_seq += 1
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": self.visitor_id,
                        "event_type": "ZONE_DWELL",
                        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "zone_id": self.current_zone,
                        "dwell_ms": dwell_time_ms,
                        "is_staff": False,
                        "confidence": 0.95,
                        "metadata": {
                            "sku_zone": self.current_zone,
                            "session_seq": self.session_seq
                        }
                    })

                # EXIT
                if self.current_zone == "Exit" and new_zone is None:
                    self.in_store = False
                    self.session_seq += 1
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": self.visitor_id,
                        "event_type": "EXIT",
                        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "zone_id": None,
                        "dwell_ms": dwell_time_ms,
                        "is_staff": False,
                        "confidence": 0.95,
                        "metadata": {
                            "session_seq": self.session_seq
                        }
                    })

            # 2. ZONE_ENTER
            if new_zone:
                self.zone_entry_time = timestamp

                # ENTRY
                if new_zone == "Entrance" and not self.in_store:
                    self.in_store = True
                    self.session_seq += 1
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": self.visitor_id,
                        "event_type": "ENTRY",
                        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "zone_id": None,
                        "dwell_ms": 0,
                        "is_staff": False,
                        "confidence": 0.98,
                        "metadata": {
                            "session_seq": self.session_seq
                        }
                    })

                # ZONE_ENTER
                self.session_seq += 1
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": self.visitor_id,
                    "event_type": "ZONE_ENTER",
                    "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "zone_id": new_zone,
                    "dwell_ms": 0,
                    "is_staff": False,
                    "confidence": 0.95,
                    "metadata": {
                        "sku_zone": new_zone,
                        "session_seq": self.session_seq
                    }
                })

                # BILLING_QUEUE_JOIN
                if new_zone == "Billing Counter":
                    self.session_seq += 1
                    # Simulate an active queue length of 3
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": self.visitor_id,
                        "event_type": "BILLING_QUEUE_JOIN",
                        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "zone_id": new_zone,
                        "dwell_ms": 0,
                        "is_staff": False,
                        "confidence": 0.96,
                        "metadata": {
                            "queue_depth": 3,
                            "session_seq": self.session_seq
                        }
                    })

                    # PURCHASE event during billing queue
                    if not self.has_billed:
                        self.has_billed = True
                        self.session_seq += 1
                        events.append({
                            "event_id": str(uuid.uuid4()),
                            "store_id": self.store_id,
                            "camera_id": self.camera_id,
                            "visitor_id": self.visitor_id,
                            "event_type": "PURCHASE",
                            "timestamp": (timestamp + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "zone_id": new_zone,
                            "dwell_ms": 0,
                            "is_staff": False,
                            "confidence": 0.99,
                            "metadata": {
                                "sku_zone": new_zone,
                                "session_seq": self.session_seq,
                                "amount": round(random.uniform(500, 3000), 2)
                            }
                        })

            self.current_zone = new_zone

        return events
