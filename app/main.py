from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.database import engine, Base
from app.db_models import DBEvent
from app.ingestion import router as ingest_router
from app.analytics_router import router as analytics_router

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Purplle Store Intelligence API",
    description="Backend API and Real-Time Dashboard for Store visitor tracking, zone analysis, and anomaly detection."
)

# Include API Routers
app.include_router(ingest_router)
app.include_router(analytics_router)

# Mount Static Files (for CSS, JS, Images)
app.mount("/static", StaticFiles(directory="dashboard"), name="static")

@app.get("/")
def serve_dashboard():
    # Return the HTML dashboard directly at root
    dashboard_path = os.path.join("dashboard", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {
        "status": "running",
        "service": "Store Intelligence API",
        "message": "Dashboard file not found. Static files mounted at /static."
    }