import logging

from tts import Engine
from tts import (
    VoiceNotFoundError, VoicePreloadError, AudioGenerationError, VoiceRetrievalError
)

from .config.app import create_app
from .exceptions.handlers import (
    TTSError, voice_not_found_handler, voice_preload_handler, 
    audio_generation_handler, voice_retrieval_handler, 
    tts_error_handler, global_exception_handler
)
from .routes.health import router as health_router
from .routes.tts import router as tts_router
from .routes.voices import router as voices_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Preload the TTS engine
Engine.preload()

# Create FastAPI app
app = create_app()

# Register exception handlers
app.add_exception_handler(VoiceNotFoundError, voice_not_found_handler)
app.add_exception_handler(VoicePreloadError, voice_preload_handler)
app.add_exception_handler(AudioGenerationError, audio_generation_handler)
app.add_exception_handler(VoiceRetrievalError, voice_retrieval_handler)
app.add_exception_handler(TTSError, tts_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include routers
app.include_router(health_router)
app.include_router(tts_router)
app.include_router(voices_router)


