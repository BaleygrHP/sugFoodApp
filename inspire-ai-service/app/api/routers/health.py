from fastapi import APIRouter
from datetime import datetime

health_router = APIRouter()


@health_router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "message": " AI Module is running"
    }
