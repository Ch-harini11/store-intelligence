# Purplle Store Intelligence System - Technical Choices Log

This document records the architectural choices made for the Apex Retail Store Intelligence platform, including options considered, LLM recommendations, final selections, and engineering rationales.

---

## 🔍 Choice 1: Computer Vision Detection & Tracking Model

### Options Considered
1. **YOLOv8-Nano + ByteTrack** (Selected)
2. **YOLOv9-Medium + DeepSORT**
3. **RT-DETR + Custom Trajectory Re-ID**

### Trade-off Analysis
- **YOLOv9 + DeepSORT** provides slightly higher detection accuracy on highly crowded frames, but DeepSORT requires extracting appearance descriptors using a separate deep feature extractor (e.g. OSNet), which increases CPU/GPU compute latency by over 3x.
- **RT-DETR** is highly accurate but too heavy for edge computing setups typically found on in-store CCTV recorders.
- **YOLOv8-Nano** coupled with **ByteTrack** was selected. ByteTrack is a high-performance association method that tracks objects by associating almost every detection box (including low-score ones to handle partial occlusions). It is incredibly fast (runs at 45+ FPS on commodity CPUs) and comes built-in with the `ultralytics` package, eliminating complex compile-time C++ dependencies in our containerized environment. This fulfills the Purplle requirement of a robust, highly performant edge pipeline that degrades gracefully under occlusion.

---

## ⚡ Choice 2: Event Schema Design Rationale

### Rationale
Our event schema is designed to be highly structured and idempotent, ensuring that raw behavioral events maps cleanly to the business metrics queries:
- **`visitor_id`**: Assigned as a unique token per shopper session. The tracker retains the ID across frames, preventing re-entry inflation (Re-entry logs as a `REENTRY` event with the same ID instead of creating a brand new customer session).
- **`event_type`**: Includes granular states (`ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, `PURCHASE`, `BILLING_QUEUE_JOIN`).
- **`dwell_ms`**: Extracted directly during the `ZONE_EXIT` or `EXIT` transition by calculating `(exit_timestamp - enter_timestamp) * 1000`. This enables direct averaging `func.avg(DBEvent.dwell_ms)` in our `/metrics` endpoint rather than complex timestamp-difference grouping on every API query, achieving sub-millisecond API response latency.
- **`session_seq`**: An ordinal tracking sequence number incremented for each visitor's event. This provides an audit trail of visitor pathways (e.g. knowing if they went from Entrance directly to Billing or spent time browsing).

---

## 🧠 Choice 3: API & Storage Architecture Choice

### Options Considered
1. **FastAPI + SQLite + SQLAlchemy** (Selected)
2. **Node.js/Express + PostgreSQL + Prisma**
3. **Flask + MongoDB + PyMongo**

### Trade-off Analysis
- **Node.js + PostgreSQL** is standard for large enterprise web dashboards, but it introduces massive boilerplate (connection pools, ORM compilation) and fails the *clean machine acceptance gate* because PostgreSQL requires starting separate Docker containers, setting credentials, and running migration scripts.
- **FastAPI + SQLite** was selected. FastAPI is incredibly fast, native to the Python ecosystem (allowing sharing of model schemas and mock generators directly), and automatically compiles OpenAPI schemas to serve a beautiful Swagger UI out-of-the-box.
- **SQLite** stores the entire database locally in a single file (`store.db`) which is mounted as a persistent host volume. This satisfies the `docker compose up` acceptance gate perfectly—anyone can clone the repo and run it instantly on a clean machine without any database provisioning steps.
- **SQLAlchemy (ORM)** was selected to abstract SQL operations. By using SQLAlchemy, we write database-agnostic code: if Apex Retail scales to 40 active stores and requires a centralized cloud PostgreSQL database, we can switch from SQLite to PostgreSQL by simply updating the `DATABASE_URL` environment variable, with zero changes to our API code.
