from fastapi import FastAPI
import asyncio
import os
from typing import List

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import ORJSONResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from tts import Engine
from .async_config import AsyncConfig

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
    , default_response_class=ORJSONResponse)

    # --- Security & performance middleware ---
    # CORS: disabled by default; enable via CORS_ALLOW_ORIGINS env (comma-separated)
    cors_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "")
    if cors_origins_env:
        allow_origins: List[str] = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"]
        )

    # Trusted hosts: restrict Host header (safe defaults for local dev)
    allowed_hosts_env = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,::1,192.168.1.64")
    allowed_hosts = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
    if allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task( Engine.preload_async())

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup resources on shutdown"""
        try:
            # Use the Engine singleton to handle shutdown of all engines
            Engine.shutdown()
                
        except Exception as e:
            pass  # Silently handle shutdown errors
    
    return app
