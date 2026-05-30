import cv2
import numpy as np
import time
import requests
import uuid
import random
from datetime import datetime

# FastAPI Ingestion endpoint
INGEST_URL = "http://127.0.0.1:8000/events/ingest"

# Define the store layout zones (pixels in 800x600 space)
ZONES = {
    "Entrance": np.array([[50, 50], [250, 50], [250, 150], [50, 150]], dtype=np.int32),
    "Shelf A": np.array([[50, 220], [350, 220], [350, 350], [50, 350]], dtype=np.int32),
    "Shelf B": np.array([[450, 220], [750, 220], [750, 350], [450, 350]], dtype=np.int32),
    "Billing Counter": np.array([[50, 420], [350, 420], [350, 550], [50, 550]], dtype=np.int32),
    "Exit": np.array([[550, 420], [750, 420], [750, 550], [550, 550]], dtype=np.int32)
}

# Color palette for zones (BGR)
ZONE_COLORS = {
    "Entrance": (0, 255, 0),        # Green
    "Shelf A": (255, 128, 0),       # Orange-blue
    "Shelf B": (255, 0, 128),       # Purple-pink
    "Billing Counter": (0, 255, 255), # Yellow
    "Exit": (0, 0, 255)            # Red
}

def is_point_in_polygon(point, polygon):
    """
    Check if a 2D point is inside a polygon using OpenCV's pointPolygonTest.
    """
    # pointPolygonTest returns >= 0 if inside or on edge
    result = cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False)
    return result >= 0

class VisitorStateTracker:
    def __init__(self, visitor_id, store_id="store_001", camera_id="Cam-CV-1"):
        self.visitor_id = visitor_id
        self.store_id = store_id
        self.camera_id = camera_id
        self.current_zone = None
        self.zone_entry_time = None
        self.in_store = False
        self.has_billed = False

    def update_position(self, point, timestamp=None):
        if not timestamp:
            timestamp = datetime.now()

        # Find current zone
        new_zone = None
        for zone_name, polygon in ZONES.items():
            if is_point_in_polygon(point, polygon):
                new_zone = zone_name
                break

        events = []

        # State transition logic
        if new_zone != self.current_zone:
            # 1. Handle Exit from previous zone
            if self.current_zone:
                dwell_time_ms = int((timestamp - self.zone_entry_time).total_seconds() * 1000)
                
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": self.visitor_id,
                    "event_type": "ZONE_EXIT",
                    "timestamp": timestamp.isoformat(),
                    "zone_id": self.current_zone,
                    "dwell_ms": dwell_time_ms,
                    "confidence": 0.95,
                    "metadata": {}
                })

                # If exiting the whole store via the Exit zone
                if self.current_zone == "Exit" and new_zone is None:
                    self.in_store = False
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": self.visitor_id,
                        "event_type": "EXIT",
                        "timestamp": timestamp.isoformat(),
                        "zone_id": "Entrance", # store exit is mapped back to the general entrance/exit log
                        "dwell_ms": dwell_time_ms,
                        "confidence": 0.95,
                        "metadata": {}
                    })

            # 2. Handle Entry into new zone
            if new_zone:
                self.zone_entry_time = timestamp

                # If entering Entrance zone (store entry)
                if new_zone == "Entrance" and not self.in_store:
                    self.in_store = True
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": self.visitor_id,
                        "event_type": "ENTRY",
                        "timestamp": timestamp.isoformat(),
                        "zone_id": "Entrance",
                        "dwell_ms": 0,
                        "confidence": 0.98,
                        "metadata": {}
                    })

                events.append({
                    "event_id": str(uuid.uuid4()),
                    "store_id": self.store_id,
                    "camera_id": self.camera_id,
                    "visitor_id": self.visitor_id,
                    "event_type": "ZONE_ENTER",
                    "timestamp": timestamp.isoformat(),
                    "zone_id": new_zone,
                    "dwell_ms": 0,
                    "confidence": 0.95,
                    "metadata": {}
                })

                # If entering Billing Counter, trigger a Purchase event after a tiny delay
                if new_zone == "Billing Counter" and not self.has_billed:
                    self.has_billed = True
                    events.append({
                        "event_id": str(uuid.uuid4()),
                        "store_id": self.store_id,
                        "camera_id": self.camera_id,
                        "visitor_id": self.visitor_id,
                        "event_type": "PURCHASE",
                        "timestamp": (timestamp + timedelta(seconds=1)).isoformat(),
                        "zone_id": "Billing Counter",
                        "dwell_ms": 0,
                        "confidence": 0.99,
                        "metadata": {
                            "amount": round(random.uniform(300, 2500), 2),
                            "items_count": random.randint(1, 5)
                        }
                    })

            self.current_zone = new_zone

        return events

def post_events(events):
    if not events:
        return
    try:
        response = requests.post(INGEST_URL, json=events, timeout=2)
        if response.status_code in [200, 201]:
            print(f"[API] Ingested {len(events)} events successfully.")
        else:
            print(f"[API Error] Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[API Error] Connection failed: {str(e)}")

def run_synthetic_simulation(fps=10, show_window=True):
    """
    Renders an interactive shop simulation window. Shoppers move between zones.
    Useful for testing the tracking logic without loading a model.
    """
    width, height = 800, 600
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Active shoppers state
    # shopper: {visitor_id, position: [x, y], target: [x, y], speed, tracker: VisitorStateTracker}
    shoppers = []
    visitor_counter = 0

    # Define path nodes
    nodes = {
        "Entrance": [150, 100],
        "Shelf A": [200, 285],
        "Shelf B": [600, 285],
        "Billing Counter": [200, 485],
        "Exit": [650, 485],
        "Outside": [700, 580]
    }

    # Sequence of target zones for shoppers
    def get_shoper_path():
        path = ["Entrance"]
        # Shelf path
        if random.random() < 0.5:
            path.append("Shelf A")
        if random.random() < 0.5:
            path.append("Shelf B")
        # Billing path
        if random.random() < 0.7:
            path.append("Billing Counter")
        path.append("Exit")
        path.append("Outside")
        return path

    print("Starting Synthetic Shop Intelligence Simulation...")
    print("Press 'ESC' or 'q' to close the simulation window.")

    while True:
        # 1. Reset frame with a clean layout
        frame.fill(20) # Dark gray background

        # Draw zones and names
        for zone_name, polygon in ZONES.items():
            color = ZONE_COLORS[zone_name]
            cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=2)
            # Add overlay
            overlay = frame.copy()
            cv2.fillPoly(overlay, [polygon], color)
            cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
            # Text
            cv2.putText(frame, zone_name, (polygon[0][0] + 10, polygon[0][1] + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Spawn new shoppers
        if len(shoppers) < 4 and random.random() < 0.05:
            visitor_counter += 1
            vid = f"Shopper-{visitor_counter:03d}"
            path = get_shoper_path()
            shoppers.append({
                "visitor_id": vid,
                "pos": np.array([150, -20], dtype=float), # start offscreen
                "path": path,
                "target_idx": 0,
                "speed": random.uniform(3.0, 6.0),
                "tracker": VisitorStateTracker(vid)
            })

        active_shoppers = []
        for s in shoppers:
            # Move towards current target node
            target_name = s["path"][s["target_idx"]]
            target_pos = np.array(nodes[target_name], dtype=float)
            
            direction = target_pos - s["pos"]
            distance = np.linalg.norm(direction)
            
            if distance > s["speed"]:
                s["pos"] += (direction / distance) * s["speed"]
                active_shoppers.append(s)
            else:
                # Reached node, move to next node in path
                s["pos"] = target_pos
                if s["target_idx"] < len(s["path"]) - 1:
                    s["target_idx"] += 1
                    active_shoppers.append(s)
                else:
                    # Shopper exited, call tracker transition to finish
                    events = s["tracker"].update_position(s["pos"])
                    post_events(events)
                    continue

            # Update tracker state and ingest events
            events = s["tracker"].update_position(s["pos"])
            post_events(events)

            # Draw Shopper
            pos_int = (int(s["pos"][0]), int(s["pos"][1]))
            # Color depending on current zone
            color = (255, 255, 255)
            if s["tracker"].current_zone:
                color = ZONE_COLORS[s["tracker"].current_zone]
            cv2.circle(frame, pos_int, 10, color, -1)
            cv2.putText(frame, s["visitor_id"], (pos_int[0] - 25, pos_int[1] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        shoppers = active_shoppers

        # HUD Info
        cv2.putText(frame, "Purplle Live Store Simulation", (20, 580),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        cv2.putText(frame, f"Active Shoppers: {len(shoppers)}", (600, 580),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        if show_window:
            cv2.imshow("Store Intelligence CV Simulator", frame)
            key = cv2.waitKey(1000 // fps) & 0xFF
            if key == 27 or key == ord('q'):
                break
        else:
            time.sleep(1 / fps)

    if show_window:
        cv2.destroyAllWindows()

def run_yolo_pipeline(source=0):
    """
    Runs YOLO person tracking on the video source.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[YOLO Error] ultralytics package is not installed. Run 'pip install ultralytics'.")
        return

    # Load YOLO Model (person class is class 0)
    model = YOLO("yolov8n.pt")
    
    # Open capture
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[Error] Failed to open video source: {source}")
        return

    trackers = {} # map tracking_id -> VisitorStateTracker

    print(f"Starting YOLO Tracking Pipeline on source {source}...")
    print("Press 'q' to stop.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Resize frame for uniform coordinate mapping
        frame = cv2.resize(frame, (800, 600))
        
        # Run YOLO with ByteTrack
        results = model.track(frame, persist=True, classes=[0], tracker="bytetrack.yaml", verbose=False)
        
        # Draw Zones
        for zone_name, polygon in ZONES.items():
            color = ZONE_COLORS[zone_name]
            cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=2)
            cv2.putText(frame, zone_name, (polygon[0][0] + 10, polygon[0][1] + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Process detections
        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()

            for box, track_id, conf in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                
                # Bottom-Center coordinate of the person
                bottom_center = (int((x1 + x2) / 2), int(y2))
                
                visitor_id = f"Visitor-{track_id:03d}"
                if visitor_id not in trackers:
                    trackers[visitor_id] = VisitorStateTracker(visitor_id)

                # Update position and post transitions
                events = trackers[visitor_id].update_position(bottom_center)
                post_events(events)

                # Draw bounding box and ID
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 0), 2)
                cv2.circle(frame, bottom_center, 5, (0, 255, 255), -1)
                cv2.putText(frame, f"ID: {visitor_id} ({conf:.2f})", (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        cv2.imshow("Store Intelligence YOLO Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    # Default to synthetic simulation, run with '--yolo' or custom video source to test real CV pipeline
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo":
        source = sys.argv[2] if len(sys.argv) > 2 else 0
        # Convert source to int if numeric
        if source.isdigit():
            source = int(source)
        run_yolo_pipeline(source)
    else:
        run_synthetic_simulation()
