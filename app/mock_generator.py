from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import uuid

from app.db_models import DBEvent

def generate_mock_data(db: Session, store_id: str = "store_001"):
    # Clear existing events
    db.query(DBEvent).filter(DBEvent.store_id == store_id).delete()
    db.commit()

    now = datetime.now()
    events = []

    # Cameras
    cam_entrance = "Cam-Entrance-1"
    cam_shelves = "Cam-Shelves-2"
    cam_billing = "Cam-Billing-3"

    # Zones
    zone_entrance = "Entrance"
    zone_shelf_a = "Shelf A"
    zone_shelf_b = "Shelf B"
    zone_billing = "Billing Counter"
    zone_exit = "Exit"

    # Let's generate 25 historical visitors who have completed their visits
    # in the last 1 hour, to establish baseline metrics.
    for i in range(1, 21):
        visitor_id = f"Visitor-{i:03d}"
        
        # Enter time between 60 minutes ago and 15 minutes ago
        enter_mins_ago = random.randint(15, 60)
        t_enter = now - timedelta(minutes=enter_mins_ago)

        # 1. ENTRY event
        events.append(DBEvent(
            event_id=str(uuid.uuid4()),
            store_id=store_id,
            camera_id=cam_entrance,
            visitor_id=visitor_id,
            event_type="ENTRY",
            timestamp=t_enter,
            zone_id=zone_entrance,
            dwell_ms=0,
            is_staff=False,
            confidence=0.98
        ))

        # 2. Zone Enter/Exit shelves
        t_current = t_enter + timedelta(seconds=random.randint(10, 30))
        
        # Visited shelves? (80% chance)
        visited_shelf = False
        if random.random() < 0.8:
            visited_shelf = True
            shelf_zone = random.choice([zone_shelf_a, zone_shelf_b])
            dwell_shelf = random.randint(30, 180) # 30s to 3m
            
            # ENTER shelf
            events.append(DBEvent(
                event_id=str(uuid.uuid4()),
                store_id=store_id,
                camera_id=cam_shelves,
                visitor_id=visitor_id,
                event_type="ZONE_ENTER",
                timestamp=t_current,
                zone_id=shelf_zone,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ))
            
            t_current += timedelta(seconds=dwell_shelf)
            
            # EXIT shelf
            events.append(DBEvent(
                event_id=str(uuid.uuid4()),
                store_id=store_id,
                camera_id=cam_shelves,
                visitor_id=visitor_id,
                event_type="ZONE_EXIT",
                timestamp=t_current,
                zone_id=shelf_zone,
                dwell_ms=dwell_shelf * 1000,
                is_staff=False,
                confidence=0.95
            ))

        # 3. Billing Counter (60% chance if visited shelf, 20% otherwise)
        t_current += timedelta(seconds=random.randint(10, 30))
        billed = False
        if (visited_shelf and random.random() < 0.75) or (not visited_shelf and random.random() < 0.2):
            billed = True
            dwell_bill = random.randint(45, 120)
            
            # ENTER billing
            events.append(DBEvent(
                event_id=str(uuid.uuid4()),
                store_id=store_id,
                camera_id=cam_billing,
                visitor_id=visitor_id,
                event_type="ZONE_ENTER",
                timestamp=t_current,
                zone_id=zone_billing,
                dwell_ms=0,
                is_staff=False,
                confidence=0.96
            ))
            
            # Purchase event during billing
            t_purchase = t_current + timedelta(seconds=random.randint(15, 30))
            events.append(DBEvent(
                event_id=str(uuid.uuid4()),
                store_id=store_id,
                camera_id=cam_billing,
                visitor_id=visitor_id,
                event_type="PURCHASE",
                timestamp=t_purchase,
                zone_id=zone_billing,
                dwell_ms=0,
                is_staff=False,
                confidence=0.99,
                event_metadata={"amount": round(random.uniform(500, 5000), 2), "items": random.randint(1, 8)}
            ))

            t_current += timedelta(seconds=dwell_bill)
            
            # EXIT billing
            events.append(DBEvent(
                event_id=str(uuid.uuid4()),
                store_id=store_id,
                camera_id=cam_billing,
                visitor_id=visitor_id,
                event_type="ZONE_EXIT",
                timestamp=t_current,
                zone_id=zone_billing,
                dwell_ms=dwell_bill * 1000,
                is_staff=False,
                confidence=0.96
            ))

        # 4. EXIT store
        t_current += timedelta(seconds=random.randint(5, 15))
        total_dwell_s = int((t_current - t_enter).total_seconds())
        events.append(DBEvent(
            event_id=str(uuid.uuid4()),
            store_id=store_id,
            camera_id=cam_entrance,
            visitor_id=visitor_id,
            event_type="EXIT",
            timestamp=t_current,
            zone_id=zone_entrance,
            dwell_ms=total_dwell_s * 1000,
            is_staff=False,
            confidence=0.97
        ))

    # --- ANOMALY: Long Queue at Billing Counter ---
    # Ingress 6 active visitors currently at the billing counter (entered billing counter 3 minutes ago, no exit events yet)
    for j in range(101, 107):
        visitor_id = f"Visitor-Queue-{j}"
        t_enter = now - timedelta(minutes=6)
        
        # ENTRY
        events.append(DBEvent(
            event_id=str(uuid.uuid4()),
            store_id=store_id,
            camera_id=cam_entrance,
            visitor_id=visitor_id,
            event_type="ENTRY",
            timestamp=t_enter,
            zone_id=zone_entrance,
            dwell_ms=0,
            confidence=0.98
        ))
        
        # ZONE_ENTER Billing
        t_bill_enter = now - timedelta(minutes=4)
        events.append(DBEvent(
            event_id=str(uuid.uuid4()),
            store_id=store_id,
            camera_id=cam_billing,
            visitor_id=visitor_id,
            event_type="ZONE_ENTER",
            timestamp=t_bill_enter,
            zone_id=zone_billing,
            dwell_ms=0,
            confidence=0.97
        ))

    # --- ANOMALY: Sudden Footfall Spike ---
    # Ingress 8 visitor entries in the last 2 minutes
    for k in range(201, 209):
        visitor_id = f"Visitor-Spike-{k}"
        t_enter = now - timedelta(seconds=random.randint(10, 110))
        events.append(DBEvent(
            event_id=str(uuid.uuid4()),
            store_id=store_id,
            camera_id=cam_entrance,
            visitor_id=visitor_id,
            event_type="ENTRY",
            timestamp=t_enter,
            zone_id=zone_entrance,
            dwell_ms=0,
            confidence=0.98
        ))

    # --- ANOMALY: Camera Failure ---
    # We will simulate that "Cam-Billing-3" stopped sending events. Its latest event is from 3 minutes ago.
    # The anomaly detector will notice that the latest event is > 2 minutes old.
    
    # Save all mock events to database
    db.add_all(events)
    db.commit()

    return len(events)
