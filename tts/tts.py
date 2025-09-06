import base64
import asyncio
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_serializer, ConfigDict
from enum import Enum

from .kokoro_engine import KokoroEngine
from .engine_interface import TTSEngineInterface

class TextToSpeechRequest(BaseModel):
    """
    Represents a request to synthesize text into speech.
    """
    
    text: str = Field(
        ...,
        description="The text to convert to speech",
        example="Hello, world! How are you today?",
        min_length=1,
        max_length=10000
    )
    voice_id: str = Field(
        ...,
        description="The voice identifier to use for synthesis. Use /voices endpoint to get available options.",
        example="kokoro.af_heart"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the request (optional)",
        example={"session_id": "abc123", "user_id": "user456"}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Hello, world! This is a test of the text-to-speech system.",
                "voice_id": "kokoro.af_heart",
                "metadata": {
                    "session_id": "demo_session_123",
                    "timestamp": "2025-09-02T12:00:00Z"
                }
            }
        }
    )

    async def execute_async(self) -> 'TextToSpeechResponse':
        """Asynchronous execution for better performance"""
        engine = Engine.from_voice_id(self.voice_id)
        audio = await engine.generate_async(self.text, self.voice_id)
        return TextToSpeechResponse(audio=audio, request=self)

    def to_json(self) -> str:
        """
        Converts a TextToSpeechRequest object into a JSON string.
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_string: str) -> 'TextToSpeechRequest':
        """
        Parses a JSON string into a TextToSpeechRequest object.
        """
        return cls.model_validate_json(json_string)

class TextToSpeechResponse(BaseModel):
    """
    Represents the response from a text-to-speech synthesis.
    """
    audio: bytes = Field(
        ...,
        description="The synthesized audio data in WAV format, encoded as base64"
    )

    @property
    def audio_base64(self) -> str:
        """Get the audio data as a base64-encoded string"""
        return base64.b64encode(self.audio).decode("utf-8")

    @field_serializer("audio")
    def serialize_audio(self, v: bytes, _info):
        return self.audio_base64

    request: TextToSpeechRequest = Field(
        ...,
        description="Echo of the original request for reference"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqF...",
                "request": {
                    "text": "Hello, world! This is a test.",
                    "voice_id": "kokoro.af_heart",
                    "metadata": {"session_id": "demo_123"}
                }
            }
        }
    )

    def to_json(self) -> str:
        """
        Converts a TextToSpeechResponse object into a JSON string.
        """
        return self.model_dump_json()

class Engine:
    _instance = None
    _initialized = False
    _engines: Dict[str, TTSEngineInterface] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Engine, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if Engine._initialized:
            return
        
        self._initialize_engines()
        Engine._initialized = True

    def _initialize_engines(self):
        """Initialize all available engine instances"""
        # Initialize Kokoro engine
        kokoro_engine = KokoroEngine.get_instance()
        self._engines['kokoro'] = kokoro_engine
        
        # Add other engines here as they become available
        # self._engines['other_engine'] = OtherEngine.get_instance()

    @classmethod
    async def preload_async(cls):
        """Asynchronous preloading of all engines for better startup performance"""
        instance = cls.get_instance()
        
        # Preload all engines concurrently
        tasks = [
            engine.preload_async() for engine in instance._engines.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    @classmethod
    def get_instance(cls) -> 'Engine':
        """Get the singleton instance of Engine"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def from_voice_id(cls, voice_id: str) -> TTSEngineInterface:
        """Get engine instance based on voice_id"""
        instance = cls.get_instance()
        
        # Determine which engine to use based on voice_id prefix
        if voice_id.startswith('kokoro.'):
            return instance._engines['kokoro']
        
        # Add logic for other engines as they become available
        # elif voice_id.startswith('other.'):
        #     return instance._engines['other_engine']
        
        # Default to kokoro for backward compatibility
        return instance._engines['kokoro']

    @classmethod
    async def get_sample_async(cls, voice_id: str) -> Optional[bytes]:
        """Asynchronous version of get_sample"""
        instance = cls.get_instance()
        return await instance._engines['kokoro'].get_sample_async(voice_id)

    async def generate_async(self, text: str, voice_id: str) -> bytes:
        """Asynchronous generate method"""
        # This method should be called on the specific engine instance
        # returned by from_voice_id(), not the main Engine class
        raise NotImplementedError("Use engine.generate_async() on the specific engine instance")

    @classmethod
    def shutdown(cls):
        """Shutdown all engines and cleanup resources"""
        instance = cls.get_instance()
        
        # Shutdown all engines - they all implement the shutdown method from the interface
        for engine_name, engine in instance._engines.items():
            try:
                engine.shutdown()
            except Exception as e:
                pass  # Silently handle shutdown errors
