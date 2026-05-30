# 🏬 Purplle Store Intelligence - Pitch Deck Slide Outline

This document provides a slide-by-slide outline for your hackathon pitch presentation. You can copy and paste this content directly into PowerPoint, Keynote, or Google Slides.

---

## 🛝 Slide 1: Title Slide (The Hook)
* **Title**: Purplle Store Intelligence System
* **Sub-title**: Bringing E-Commerce Analytics Parity to Physical Retail Stores
* **Presenter**: Apex Retail Analytics Solutions Team
* **Visual Concept**: Sleek, modern dark-mode aesthetic with neon accents (purple, blue, and green) framing a retail surveillance camera icon.

---

## 🛝 Slide 2: The Business Problem (The Pain Point)
* **Header**: The Offline Retail Data Blind Spot
* **Key Bullet Points**:
  - **Online Parity**: Online channels track every click, scroll, cart addition, and bounce rate in real-time.
  - **Offline Blind Spot**: Physical stores represent 90% of revenue but have zero behavioral analytics.
  - **The Cost**: Retail managers have no data on customer browse paths, product engagement, queue bottlenecks, or drop-off rates before purchase.
* **Core Metric**: Apex Retail operates 40 physical stores across 8 cities in complete statistical darkness.

---

## 🛝 Slide 3: The Solution (The Innovation)
* **Header**: End-to-End AI-Powered Retail Intelligence
* **Key Bullet Points**:
  - **Edge Video Pipeline**: Transforms existing raw CCTV footage into structured, real-time event streams.
  - **Zero Manual Overhead**: Fully automated person detection, spatial zone tracking, and metrics aggregation.
  - **Actionable Insights**: Feeds live dashboards with conversion funnels, dwell times, and operational anomaly logs.
* **Key Quote**: *"A fully containerized system that turns CCTV frames into operational store decisions."*

---

## 🛝 Slide 4: Technical Pipeline Architecture (How it Works)
* **Header**: High-Performance Data Flow
* **Flowchart Layout**:
  ```text
   сурveillance Clips (Entry, Floor, Billing Camera Angles)
          ↓
    YOLOv8 Detection (Person class detection & confidence logging)
          ↓
    ByteTrack Association (Persistent tracking visitor session IDs)
          ↓
    Event Engine (OpenCV 2D polygon intersection & dwell timing)
          ↓
    SQLite Storage (Bulk pre-fetch deduplication to keep API idempotent)
          ↓
    FastAPI Core (Metrics, Funnels, and Occupancy RESTful services)
          ↓
    Web Dashboard (Auto-polling Chart.js graphs & visual floor cell indicators)
  ```

---

## 🛝 Slide 5: Spatial Zone Intelligence
* **Header**: High-Precision Store Mapping
* **Key Bullet Points**:
  - **Polygon Zoning**: Store layout defined as 2D spatial coordinate polygons (Entrance, Shelf A, Shelf B, Billing, Exit).
  - **Point-in-Polygon Engine**: Maps the bottom-center of the visitor's bounding box and checks containment using OpenCV `cv2.pointPolygonTest`.
  - **Sequence State Tracking**: Logs visitor movements chronologically, tracking `session_seq` to analyze exact browse pathways.
  - **Dwell Time Resolution**: Calculates precise times spent in individual zones in milliseconds upon zone exits.

---

## 🛝 Slide 6: Real-Time Operational Anomalies Engine
* **Header**: Automated Store Supervision & Alerts
* **Key Bullet Points**:
  - **Camera Failure (`CAMERA_FAILURE`)**: Triggers a critical warning if any camera feed goes silent for over 2 minutes.
  - **Long Billing Queue (`LONG_QUEUE`)**: Triggers an alert if more than 5 active shoppers are waiting at checkout, suggesting staff dispatch.
  - **Sudden Footfall Spike (`FOOTFALL_SPIKE`)**: Flags if entrances in the last 5 minutes exceed 3x the running hourly average.
  - **Empty Store (`EMPTY_STORE`)**: Alerts managers if zero visitors are active in the store for over 30 minutes during core business hours.

---

## 🛝 Slide 7: Conversion Funnel & Business Metrics
* **Header**: Tracking the Shopper Journey
* **Key Bullet Points**:
  - **The Funnel**: Entered Store → Visited Shelf (A or B) → Billed at Checkout.
  - **Drop-off Analysis**: Pinpoints exactly where customers lose interest or experience friction.
  - **Idempotency & Re-entry**: Sessionization logic ensures re-entering customers are tracked in the same session without double-counting unique visitors.
  - **Peak Hour Detection**: Isolates high-traffic time windows to allocate personnel and store operations effectively.

---

## 🛝 Slide 8: Premium Glassmorphic Web Dashboard
* **Header**: Human-Centric Operational Dashboard
* **Key Bullet Points**:
  - **Premium UI Design**: Built with glassmorphism blur layers, custom deep radial gradients, and neon warning indicators.
  - **Auto-Polling Update**: Fetches metrics, occupancy cells, and anomalies every 3 seconds to keep the dashboard live.
  - **Floor Occupancy Visualizer**: Integrates a CSS grid displaying occupant density across spatial cells dynamically.
  - **Control Interface**: Includes buttons to trigger mock data simulation or reset the SQLite database.

---

## 🛝 Slide 9: Production Readiness & Containerization
* **Header**: Built for Operations & Scale
* **Key Bullet Points**:
  - **One-Command Build**: `docker-compose up --build -d` compiles uvicorn, installs Mesa graphics drivers, and runs the dashboard.
  - **Database Persistence**: SQLite database file (`store.db`) is mapped as a persistent volume to preserve data across restarts.
  - **Bulk Deduplication**: API pre-fetches IDs in a single SQL operation, keeping ingestion endpoints idempotent and ultra-fast.
  - **Clean Code Verification**: Fully validated test suite showing 100% passing rates.

---

## 🛝 Slide 10: Conclusion & Core Strengths (Why We Win)
* **Header**: Transforming CCTV into Offline Parity
* **Key Bullet Points**:
  - **Edge-Ready & Robust**: Designed to run locally on low-cost edge computers inside stores.
  - **Highly Modular**: Decoupled routes (`metrics.py`, `funnel.py`, `anomalies.py`, `health.py`) allow easy maintenance and expansion.
  - **Scale-Ready**: SQLAlchemy models support switching from SQLite to PostgreSQL with a single configuration environment string.
* **Submission Checklist**: Git Repo + README.md + DESIGN.md + CHOICES.md + Pitch Deck + Working Live Dashboard.
