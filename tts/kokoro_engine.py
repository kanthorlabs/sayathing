from typing import Optional
from kokoro import KPipeline
import soundfile as sf
import torch
import base64
import io
import json
import os

from .voices import Voices, VOICE_SAMPLE


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
        
        # Preload all voices to prevent cold starts
        self._preload_voices()
        
        KokoroEngine._initialized = True
        print(f"KokoroEngine initialized with {len(self._preloaded_voices)} voices preloaded")

    def _preload_voices(self):
        for voice_id in Voices.get_all().keys():
            try:
                voice_name = voice_id.split(".")[1] if "." in voice_id else voice_id
                print(f"Preloading voice: {voice_name}")
                
                # Use the generate method to warm up the voice
                audio_bytes = self._generate_audio(VOICE_SAMPLE, voice_id)
                
                # Store the actual audio bytes data  
                self._preloaded_voices[voice_id] = audio_bytes
                print(f"✓ Voice {voice_name} preloaded successfully ({len(audio_bytes)} bytes)")
                
            except Exception as e:
                print(f"✗ Failed to preload voice {voice_name}: {e}")
                self._preloaded_voices[voice_id] = None

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

    def generate(self, text: str, voice_id: str) -> bytes:
        # Validate voice_id is in available voices
        available_voices = list(Voices.get_all().keys())
        if voice_id not in available_voices:
            raise VoiceNotFoundError(voice_id, available_voices)
        
        # Check if voice was successfully preloaded
        if self._preloaded_voices.get(voice_id) is None:
            raise VoicePreloadError(voice_id)
        
        # Generate fresh audio for the requested text
        return self._generate_audio(text, voice_id)

    @classmethod 
    def get_instance(cls) -> 'KokoroEngine':
        """Get the singleton instance of KokoroEngine"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_sample(cls, voice_id: str) -> Optional[bytes]:
        instance = cls.get_instance()
        return instance._preloaded_voices.get(voice_id)