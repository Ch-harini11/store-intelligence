# 🏬 Purplle Store Intelligence System

## 🌟 Project Overview
The Purplle Store Intelligence System is an end-to-end, production-ready retail analytics platform. It leverages state-of-the-art computer vision to track shoppers, monitor spatial zone occupancy, compute retail funnel conversion, detect operational anomalies, and display live metrics in a premium web dashboard.

## 🧠 AI Powered Store Intelligence System
Surveillance cameras capture live store footfall. Using deep learning models (YOLOv8) for person detection and ByteTrack for multi-object tracking, the system builds an accurate map of shopper pathways. Spatial analytics determine when visitors enter shelves, wait at billing lines, or exit, generating structured store events which are ingested and analyzed to drive real-time operational optimization.

---

## 🏗️ Architecture

```text
 CCTV Camera Feed
        ↓
  YOLO Detection (Person Filtering)
        ↓
  ByteTrack Multi-Object Tracking
        ↓
  Event Generation Engine (Zone Crossings & Dwell Times)
        ↓
  SQLite Database (Local Persistence with Bulk Deduplication)
        ↓
  FastAPI Web Service (Metrics, Funnels, and Occupancy REST APIs)
        ↓
  Glassmorphic Web Dashboard (Chart.js & Live Floor Occupancy)
```

---

## ⚡ Features

* **Footfall Analytics**: Monitors unique customer entrances and total visitor frequency.
* **Occupancy Monitoring**: Computes live customer distribution across the store in real-time.
* **Conversion Funnel**: Tracks the standard retail flow (Entered → Visited Shelf → Checked Out / Billed) and computes the store's conversion rate.
* **Zone Analytics**: Measures individual zone occupancy (Entrance, Shelf A, Shelf B, Billing Counter, Exit).
* **Dwell Time Analysis**: Tracks visitor dwell times in milliseconds for each zone, providing details on product engagement and queue delays.
* **Peak Hour Detection**: Identifies busy entrance time slots to optimize staff scheduling.
* **Anomaly Detection**: Scans store logs to trigger critical warnings (e.g. camera failures, long billing lines, empty store during business hours, footfall spikes).

---

## 💻 Installation & Setup

Follow these commands to install and start the system locally:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ch-harini11/budgetwise.git store-intelligence
   cd store-intelligence
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   # Create environment
   python -m venv venv

   # Activate environment (Windows)
   venv\Scripts\activate

   # Activate environment (macOS/Linux)
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the FastAPI Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

Open your browser and navigate to **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** to access the live dashboard.

---

## 🐳 Docker Deployment

To build and run the entire store intelligence web server in an isolated container:

1. **Start the container**:
   ```bash
   docker-compose up --build -d
   ```
2. **Access the system**:
   - Web Dashboard: `http://localhost:8000/`
   - Interactive API docs: `http://localhost:8000/docs`
   - Database Persistence: SQLite file is mounted locally at `./store.db`.
