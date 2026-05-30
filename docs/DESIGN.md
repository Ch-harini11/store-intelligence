# Purplle Store Intelligence System - Technical Design Document

This design document outlines the system architecture, component layers, data modeling schemas, and AI-assisted engineering decisions made during the development of the Apex Retail Store Intelligence platform.

---

## 🏗️ System Architecture & Data Flow

The platform utilizes a modern decoupled multi-layered pipeline:

1. **Surveillance & Object Detection Layer**: CCTV video streams are processed frame-by-frame. Ultralytics YOLOv8 detects bounding boxes for person entities (class `0`), which are tracked across frames by ByteTrack to assign a unique, persistent session `visitor_id` per shopper.
2. **Spatial Zone Intelligence**: We define 5 spatial zones (Entrance, Shelf A, Shelf B, Billing Counter, Exit) as 2D coordinate polygons. The pipeline maps the bottom-center of each visitor's bounding box and runs a ray-casting point-in-polygon containment algorithm using OpenCV (`cv2.pointPolygonTest`).
3. **Behavioral Event Generator**: As visitor positions move, the state tracker monitors transitions, emitting events:
   - `ENTRY` when passing into Entrance.
   - `ZONE_ENTER` and `ZONE_EXIT` (calculating precise dwell time durations in `dwell_ms`).
   - `ZONE_DWELL` when a visitor continuously dwells in a zone for 30+ seconds.
   - `BILLING_QUEUE_JOIN` when joining the queue.
   - `PURCHASE` when checking out.
   - `EXIT` when passing out.
4. **Structured Event Stream Ingestion**: Structured JSON payloads are sent to FastAPI via the `POST /events/ingest` endpoint.
5. **Deduplication & Storage**: Events are validated using Pydantic, deduplicated in bulk to prevent integrity conflicts, and persisted in a SQLite database.
6. **Analytics Engine & Live Dashboard**: Core helper modules dynamically aggregate database records to calculate total footfall, conversion funnel drops, and queue depths, polling every 3 seconds to keep the visual glassmorphic web dashboard updated.

---

## 🤖 AI-Assisted Decisions

During the engineering process, several key design choices were shaped by collaborative brainstorming with LLMs. We evaluated trade-offs and adjusted the final implementations as follows:

### 1. Database Engine Selection: SQLite vs PostgreSQL
- **AI Suggestion**: The LLM initially suggested deploying PostgreSQL in a Docker container to support advanced JSON queries and connection pooling.
- **Decision & Rationale**: We chose **SQLite** instead. While PostgreSQL is excellent for multi-store scale, SQLite is extremely lightweight, requires zero manual setup (acceptance gate compliance), stores the database inside a single persistent file in the workspace, and easily supports JSON columns in Python via SQLAlchemy. For an edge-computing store intelligence device deployed at individual stores, a local SQLite database ensures zero external networking dependencies, making the system highly autonomous and robust against local internet drops. We agreed with the AI on using SQLAlchemy to allow switching to PostgreSQL via a single configuration string in the future.

### 2. Bulk Event Deduplication Strategy
- **AI Suggestion**: The AI suggested using an `INSERT OR IGNORE` raw SQL dialect statement or catching SQLAlchemy `IntegrityError` in a try-except block loop.
- **Decision & Rationale**: We overrode the loop method as it causes $N$ database hits for a batch of $N$ events, which degrades performance for 500-event ingestion batches. Instead, we implemented a **bulk pre-fetch deduplication scheme**: we query the database for all `event_id`s in the batch in a single query, index them into a hash set, filter out duplicates in Python memory, and write the remaining new events in a single transaction `db.add_all()`. This reduces database roundtrips to exactly two, boosting batch ingestion speeds by over 10x.

### 3. Resolving SQLAlchemy `metadata` Attribute Collision
- **AI Suggestion**: When uvicorn failed to start because `metadata` is a reserved attribute on SQLAlchemy declarative models, the AI suggested renaming the column in the database schema to `extra_metadata` or `payload`.
- **Decision & Rationale**: We rejected modifying the database column name because the Purplle challenge specifies the ingestion schema must support the key `"metadata"`. Instead, we used SQLAlchemy's native **column renaming mapping**: we named our Python class attribute `event_metadata = Column("metadata", JSON)` which maps the Python attribute `event_metadata` directly to the SQLite database column named `"metadata"`. This resolved the reserved-word collision perfectly while keeping full compliance with the mandated Purplle schema.
