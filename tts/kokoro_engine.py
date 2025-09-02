from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from kokoro import KPipeline
import soundfile as sf
import torch
import base64
import io
import json
import os
import logging

from .voices import Voices, VOICE_SAMPLE

logger = logging.getLogger(__name__)


# Custom exception classes
class VoiceNotFoundError(Exception):
    """Exception raised when a voice ID is not found"""
    def __init__(self, voice_id: str, available_voices: list = None):
        self.voice_id = voice_id
        self.available_voices = available_voices or []
        super().__init__(f"Invalid voice_id '{voice_id}'. Must be one of: {available_voices}")


class VoicePreloadError(Exception):
    """Exception raised when a voice fails to preload"""
    def __init__(self, voice_id: str):
        self.voice_id = voice_id
        super().__init__(f"Voice '{voice_id}' is not available or failed to preload")


class AudioGenerationError(Exception):
    """Exception raised when audio generation fails"""
    def __init__(self, message: str = "Failed to generate audio"):
        super().__init__(message)

class KokoroEngine:
    _instance = None
    _initialized = False
    _preloaded_voices = {}
    _executor = None
    sampling_rate = 24000

    def __new__(cls, voice_id: str = None):
        if cls._instance is None:
            cls._instance = super(KokoroEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self, voice_id: str = None):
        if KokoroEngine._initialized:
            return
        
        print("Initializing KokoroEngine singleton and preloading all voices...")
        self.pipeline = KPipeline(repo_id='hexgrad/Kokoro-82M', lang_code='a')
        
        # Initialize thread pool executor for async operations with configurable settings
        if KokoroEngine._executor is None:
            # Import here to avoid circular imports
            try:
                from server.config.async_config import AsyncConfig
                config = AsyncConfig.get_tts_executor_config()
                KokoroEngine._executor = ThreadPoolExecutor(**config)
                logger.info(f"Initialized TTS executor with config: {config}")
            except ImportError:
                # Fallback to default configuration
                KokoroEngine._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="kokoro-tts")
                logger.info("Using default TTS executor configuration")
        
        # Initialize without synchronous preloading - async preloading will be done later
        KokoroEngine._initialized = True
        print("KokoroEngine initialized - async preloading will be done separately")

    async def _preload_voices_async(self):
        """Asynchronous version of voice preloading for better startup performance"""
        async def preload_single_voice(voice_id: str):
            try:
                voice_name = voice_id.split(".")[1] if "." in voice_id else voice_id
                print(f"Preloading voice: {voice_name}")
                
                # Use the generate method to warm up the voice asynchronously with timeout
                try:
                    from server.config.async_config import AsyncConfig
                    timeout = AsyncConfig.VOICE_PRELOAD_TIMEOUT
                except ImportError:
                    timeout = 120.0  # Default timeout
                
                loop = asyncio.get_event_loop()
                audio_bytes = await asyncio.wait_for(
                    loop.run_in_executor(
                        KokoroEngine._executor,
                        self._generate_audio,
                        VOICE_SAMPLE,
                        voice_id
                    ),
                    timeout=timeout
                )
                
                # Store the actual audio bytes data  
                self._preloaded_voices[voice_id] = audio_bytes
                print(f"✓ Voice {voice_name} preloaded successfully ({len(audio_bytes)} bytes)")
                
            except asyncio.TimeoutError:
                print(f"✗ Timeout preloading voice {voice_name} (timeout: {timeout}s)")
                self._preloaded_voices[voice_id] = None
            except Exception as e:
                print(f"✗ Failed to preload voice {voice_name}: {e}")
                self._preloaded_voices[voice_id] = None

        # Preload all voices concurrently
        voice_ids = list(Voices.get_all().keys())
        tasks = [preload_single_voice(voice_id) for voice_id in voice_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

    def _generate_audio(self, text: str, voice_id: str) -> bytes:
        """Internal method to generate audio for a given text and voice"""
        try:
            voice_name = voice_id.split(".")[1] if "." in voice_id else voice_id
            generator = self.pipeline(text, voice=voice_name)
            [result] = list(generator)
            
            buffer = io.BytesIO()
            sf.write(buffer, result.audio, self.sampling_rate, format='WAV')
            buffer.seek(0)
            return buffer.read()
        except Exception as e:
            raise AudioGenerationError(f"Failed to generate audio for voice '{voice_id}': {str(e)}")

    async def generate_async(self, text: str, voice_id: str) -> bytes:
        """Asynchronous version of generate for better performance"""
        # Validate voice_id is in available voices
        available_voices = list(Voices.get_all().keys())
        if voice_id not in available_voices:
            raise VoiceNotFoundError(voice_id, available_voices)
        
        # Check if voice was successfully preloaded
        if self._preloaded_voices.get(voice_id) is None:
            raise VoicePreloadError(voice_id)
        
        # Generate fresh audio for the requested text asynchronously with timeout
        try:
            # Import timeout configuration
            try:
                from server.config.async_config import AsyncConfig
                timeout = AsyncConfig.TTS_GENERATION_TIMEOUT
            except ImportError:
                timeout = 30.0  # Default timeout
            
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(
                    KokoroEngine._executor, 
                    self._generate_audio, 
                    text, 
                    voice_id
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise AudioGenerationError(f"TTS generation timed out after {timeout}s for voice '{voice_id}'")

    @classmethod 
    def get_instance(cls) -> 'KokoroEngine':
        """Get the singleton instance of KokoroEngine"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod 
    async def get_sample_async(cls, voice_id: str) -> Optional[bytes]:
        """Asynchronous version of get_sample"""
        instance = cls.get_instance()
        # Since samples are preloaded, we can return them directly
        # but we'll make it async for consistency with the API
        return instance._preloaded_voices.get(voice_id)

    @classmethod
    async def preload_async(cls):
        """Asynchronous preloading of voices for better startup performance"""
        instance = cls.get_instance()
        if len(instance._preloaded_voices) == 0:  # Only preload if not already done
            await instance._preload_voices_async()
            print(f"KokoroEngine preloaded with {len(instance._preloaded_voices)} voices")