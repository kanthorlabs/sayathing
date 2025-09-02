from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()

@router.get(
    "/healthz",
    tags=["health"],
    summary="Health Check",
    description="Returns the current health status of the TTS service",
    response_description="Service health information including version and timestamp",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "version": "25.9.1",
                        "timestamp": "2025-09-02T12:00:00.000Z"
                    }
                }
            }
        }
    }
)
async def healthz():
    """
    Check the health status of the TTS service.
    
    Returns basic service information including:
    - Current version number
    - Current UTC timestamp
    """
    return {
        "version": "25.9.1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
