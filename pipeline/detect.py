import cv2
import numpy as np
import time
import sys
import random
from datetime import datetime

from pipeline.tracker import ZONES, ZONE_COLORS, VisitorStateTracker
from pipeline.emit import post_events

def run_synthetic_simulation(fps=10, show_window=True):
    """
    Simulates moving circles as shoppers inside a store floor layout.
    Generates and POSTs structured events to the uvicorn ingestion API.
    """
    width, height = 800, 600
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    shoppers = []
    visitor_counter = 0

    nodes = {
        "Entrance": [150, 100],
        "Shelf A": [200, 285],
        "Shelf B": [600, 285],
        "Billing Counter": [200, 485],
        "Exit": [650, 485],
        "Outside": [700, 580]
    }

    def get_shopper_path():
        path = ["Entrance"]
        if random.random() < 0.5:
            path.append("Shelf A")
        if random.random() < 0.5:
            path.append("Shelf B")
        if random.random() < 0.7:
            path.append("Billing Counter")
        path.append("Exit")
        path.append("Outside")
        return path

    print("[PIPELINE] Starting Synthetic Retail Floor Simulator...")
    print("[PIPELINE] Press 'ESC' or 'q' inside the OpenCV window to terminate.")

    while True:
        frame.fill(20)

        # Draw zones and overlays
        for zone_name, polygon in ZONES.items():
            color = ZONE_COLORS[zone_name]
            cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=2)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [polygon], color)
            cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
            cv2.putText(frame, zone_name, (polygon[0][0] + 10, polygon[0][1] + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Spawn new shoppers
        if len(shoppers) < 4 and random.random() < 0.05:
            visitor_counter += 1
            vid = f"VIS_{visitor_counter:03x}" # Unique visit token
            path = get_shopper_path()
            shoppers.append({
                "visitor_id": vid,
                "pos": np.array([150, -20], dtype=float),
                "path": path,
                "target_idx": 0,
                "speed": random.uniform(3.0, 6.0),
                "tracker": VisitorStateTracker(vid)
            })

        active_shoppers = []
        for s in shoppers:
            target_name = s["path"][s["target_idx"]]
            target_pos = np.array(nodes[target_name], dtype=float)
            
            direction = target_pos - s["pos"]
            distance = np.linalg.norm(direction)
            
            if distance > s["speed"]:
                s["pos"] += (direction / distance) * s["speed"]
                active_shoppers.append(s)
            else:
                s["pos"] = target_pos
                if s["target_idx"] < len(s["path"]) - 1:
                    s["target_idx"] += 1
                    active_shoppers.append(s)
                else:
                    events = s["tracker"].update_position(s["pos"])
                    post_events(events)
                    continue

            events = s["tracker"].update_position(s["pos"])
            post_events(events)

            # Render shoppers
            pos_int = (int(s["pos"][0]), int(s["pos"][1]))
            color = (255, 255, 255)
            if s["tracker"].current_zone:
                color = ZONE_COLORS[s["tracker"].current_zone]
            cv2.circle(frame, pos_int, 10, color, -1)
            cv2.putText(frame, s["visitor_id"], (pos_int[0] - 25, pos_int[1] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        shoppers = active_shoppers

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
    Main YOLO tracking and zone crossing detection thread.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[PIPELINE ERROR] ultralytics is not installed. Install via pip install ultralytics.")
        return

    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[PIPELINE ERROR] Failed to open source: {source}")
        return

    trackers = {}

    print(f"[PIPELINE] Launching YOLO tracking pipeline on source {source}...")
    print("[PIPELINE] Press 'q' inside the OpenCV window to terminate.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.resize(frame, (800, 600))
        
        # PERSIST=True tracks across frames with ByteTrack
        results = model.track(frame, persist=True, classes=[0], tracker="bytetrack.yaml", verbose=False)
        
        # Render polygons
        for zone_name, polygon in ZONES.items():
            color = ZONE_COLORS[zone_name]
            cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=2)
            cv2.putText(frame, zone_name, (polygon[0][0] + 10, polygon[0][1] + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()

            for box, track_id, conf in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                
                # Point of interest is the bottom-center point of bounding box
                bottom_center = (int((x1 + x2) / 2), int(y2))
                
                visitor_id = f"VIS_{track_id:03x}"
                if visitor_id not in trackers:
                    trackers[visitor_id] = VisitorStateTracker(visitor_id)

                events = trackers[visitor_id].update_position(bottom_center)
                post_events(events)

                # Draw tracking overlays
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
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo":
        src = sys.argv[2] if len(sys.argv) > 2 else 0
        if src.isdigit():
            src = int(src)
        run_yolo_pipeline(src)
    else:
        run_synthetic_simulation()
