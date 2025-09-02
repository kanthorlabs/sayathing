from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

from tts import (
    VoiceNotFoundError, VoicePreloadError, AudioGenerationError, VoiceRetrievalError
)


# Base TTS exception class for FastAPI
class TTSError(Exception):
    """Base exception for TTS-related errors"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


async def voice_not_found_handler(request: Request, exc: VoiceNotFoundError):
    """Handle voice not found errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


async def voice_preload_handler(request: Request, exc: VoicePreloadError):
    """Handle voice preload errors"""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)}
    )


async def audio_generation_handler(request: Request, exc: AudioGenerationError):
    """Handle audio generation errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


async def voice_retrieval_handler(request: Request, exc: VoiceRetrievalError):
    """Handle voice retrieval errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


async def tts_error_handler(request: Request, exc: TTSError):
    """Handle general TTS errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that logs all unhandled exceptions with stack traces.
    """
    logging.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error occurred. Please check the server logs for more details."
        }
    )
