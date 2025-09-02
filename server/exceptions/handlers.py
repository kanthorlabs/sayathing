import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse

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


logger = logging.getLogger(__name__)


async def voice_not_found_handler(request: Request, exc: VoiceNotFoundError):
    """Handle voice not found errors"""
    voice_id = getattr(exc, 'voice_id', 'unknown')
    logger.warning(f"Voice not found: {voice_id} for {request.method} {request.url}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


async def voice_preload_handler(request: Request, exc: VoicePreloadError):
    """Handle voice preload errors"""
    voice_id = getattr(exc, 'voice_id', 'unknown')
    logger.error(f"Voice preload failed: {voice_id} for {request.method} {request.url}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)}
    )


async def audio_generation_handler(request: Request, exc: AudioGenerationError):
    """Handle audio generation errors"""
    logger.error(f"Audio generation failed for {request.method} {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


async def voice_retrieval_handler(request: Request, exc: VoiceRetrievalError):
    """Handle voice retrieval errors"""
    logger.error(f"Voice retrieval failed for {request.method} {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


async def tts_error_handler(request: Request, exc: TTSError):
    """Handle general TTS errors"""
    logger.error(f"TTS error occurred for {request.method} {request.url}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that logs all unhandled exceptions with stack traces.
    """
    logger.error(
        f"Unhandled exception occurred while processing {request.method} {request.url}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error occurred. Please check the server logs for more details."
        }
    )
