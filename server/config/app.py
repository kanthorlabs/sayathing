from fastapi import FastAPI
import asyncio
import logging

logger = logging.getLogger(__name__)

# OpenAPI metadata
def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="SayAThing TTS API",
        description="""
        A high-quality Text-to-Speech (TTS) API powered by Kokoro engine.
        
        ## Features
        
        * **Multiple Voices**: Support for various voice types including American Female, American Male, British Female, and British Male voices
        * **High Quality**: Powered by Kokoro TTS engine for natural-sounding speech synthesis
        * **Base64 Audio**: Returns audio as base64-encoded data for easy integration
        
        ## Voice Types
        
        The API supports various voice types with different characteristics:
        
        * **AF_** prefix: American Female voices
        * **AM_** prefix: American Male voices  
        * **BF_** prefix: British Female voices
        * **BM_** prefix: British Male voices
        
        ## Usage
        
        1. Send a POST request to `/tts` with text and voice_id
        2. Receive base64-encoded audio in the response
        3. Decode and play the audio in your application
        """,
        version="25.9.1",
        contact={
            "name": "Kanthor Labs",
            "url": "https://kanthorlabs.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=[
            {
                "name": "health",
                "description": "Health check and system status endpoints",
            },
            {
                "name": "tts",
                "description": "Text-to-Speech synthesis operations",
            },
            {
                "name": "voices",
                "description": "Voice management and information",
            },
        ]
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize TTS engines asynchronously on startup"""
        try:
            logger.info("Starting async TTS engine preloading...")
            
            # Log async configuration
            try:
                from .async_config import AsyncConfig
                AsyncConfig.log_config()
            except ImportError:
                logger.info("Using default async configuration")
            
            from tts import Engine
            await Engine.preload_async()
            logger.info("TTS engines preloaded successfully")
        except Exception as e:
            logger.error(f"Failed to preload TTS engines: {e}")
            raise  # Re-raise to prevent startup if engines fail to load

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup resources on shutdown"""
        try:
            logger.info("Shutting down TTS engines...")
            from tts.kokoro_engine import KokoroEngine
            
            # Shutdown the thread pool executor
            if KokoroEngine._executor is not None:
                logger.info("Shutting down TTS thread pool executor...")
                KokoroEngine._executor.shutdown(wait=True, cancel_futures=True)
                logger.info("TTS thread pool executor shut down successfully")
                
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    return app
