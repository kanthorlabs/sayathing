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

from .voices import Voices, VOICE_SAMPLE
from .engine_interface import TTSEngineInterface
from server.config.config import Config


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

class KokoroEngine(TTSEngineInterface):
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
        
        self.pipeline = KPipeline(repo_id='hexgrad/Kokoro-82M', lang_code='a')
        
        # Initialize thread pool executor for async operations with configurable settings
        if KokoroEngine._executor is None:
            config = Config.get_tts_executor_config()
            KokoroEngine._executor = ThreadPoolExecutor(**config)
        
        # Initialize without synchronous preloading - async preloading will be done later
        KokoroEngine._initialized = True

    async def _preload_voices_async(self):
        """Asynchronous version of voice preloading for better startup performance"""
        async def preload_single_voice(voice_id: str):
            try:
                voice_name = voice_id.split(".")[1] if "." in voice_id else voice_id
                
                # Use the generate method to warm up the voice asynchronously with timeout
                timeout = Config.VOICE_PRELOAD_TIMEOUT
                
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
                
            except asyncio.TimeoutError:
                self._preloaded_voices[voice_id] = None
            except Exception as e:
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
        
        # Check if voice was successfully preloaded, if not try to use it anyway
        # This allows the system to work even if preload failed or hasn't completed
        if self._preloaded_voices.get(voice_id) is None:
            # Voice not preloaded, but we can still try to generate audio on-demand
            # Only log a warning for debugging purposes
            import logging
            logging.debug(f"Voice '{voice_id}' not preloaded, generating on-demand")
        
        # Generate fresh audio for the requested text asynchronously with timeout
        try:
            timeout = Config.TTS_GENERATION_TIMEOUT
            
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
        """Asynchronous version of get_sample with on-demand generation if not preloaded"""
        instance = cls.get_instance()
        
        # Check if sample was preloaded
        preloaded_sample = instance._preloaded_voices.get(voice_id)
        if preloaded_sample is not None:
            return preloaded_sample
        
        # Sample not preloaded, generate on-demand
        try:
            # Validate voice_id first
            available_voices = list(Voices.get_all().keys())
            if voice_id not in available_voices:
                return None
            
            # Generate sample on-demand
            import logging
            logging.debug(f"Sample for voice '{voice_id}' not preloaded, generating on-demand")
            
            timeout = Config.TTS_GENERATION_TIMEOUT
            loop = asyncio.get_event_loop()
            sample = await asyncio.wait_for(
                loop.run_in_executor(
                    cls._executor,
                    instance._generate_audio,
                    VOICE_SAMPLE,
                    voice_id
                ),
                timeout=timeout
            )
            
            # Cache the generated sample for future use
            instance._preloaded_voices[voice_id] = sample
            return sample
            
        except Exception as e:
            # Log error but don't fail - return None to indicate sample unavailable
            import logging
            logging.warning(f"Failed to generate sample for voice '{voice_id}': {e}")
            return None

    @classmethod
    async def preload_async(cls):
        """Asynchronous preloading of voices for better startup performance"""
        instance = cls.get_instance()
        if len(instance._preloaded_voices) == 0:  # Only preload if not already done
            await instance._preload_voices_async()

    @classmethod
    def shutdown(cls):
        """Shutdown the KokoroEngine and cleanup resources"""
        try:
            # Shutdown the thread pool executor
            if cls._executor is not None:
                cls._executor.shutdown(wait=True, cancel_futures=True)
                cls._executor = None
                
            # Clear preloaded voices cache
            if cls._instance is not None:
                cls._instance._preloaded_voices.clear()
                
            # Reset singleton state
            cls._instance = None
            cls._initialized = False
            
        except Exception as e:
            # Silently handle shutdown errors to avoid application crashes during shutdown
            pass