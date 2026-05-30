from fastapi import FastAPI
from app.ingestion import router as ingest_router

app = FastAPI(
    title="Purplle Store Intelligence API"
)

app.include_router(ingest_router)

@app.get("/")
def home():
    return {
        "status": "running",
        "service": "Store Intelligence"
    }