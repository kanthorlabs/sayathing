from tts import (AudioGenerationError, VoiceNotFoundError, VoicePreloadError,
                 VoiceRetrievalError)

from .config.app import create_app
from .exceptions.handlers import (TTSError, audio_generation_handler,
                                  global_exception_handler, tts_error_handler,
                                  voice_not_found_handler,
                                  voice_preload_handler,
                                  voice_retrieval_handler)
from .routes.health import router as health_router
from .routes.tts import router as tts_router
from .routes.voice import router as voice_router
from .routes.dashboard import router as dashboard_router

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
app.include_router(voice_router)
app.include_router(dashboard_router)
