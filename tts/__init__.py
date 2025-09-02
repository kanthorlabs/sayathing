"""
TTS (Text-to-Speech) module for generating speech from text.

This module provides voice synthesis capabilities using various voice engines.
"""

from .voices import Voice, Voices, VoiceRetrievalError
from .tts import Engine, TextToSpeechRequest, TextToSpeechResponse
from .kokoro_engine import VoiceNotFoundError, VoicePreloadError, AudioGenerationError

__all__ = [
    "Voice",
    "Voices", 
    "VoiceRetrievalError",
    "Engine",
    "TextToSpeechRequest",
    "TextToSpeechResponse",
    "VoiceNotFoundError",
    "VoicePreloadError", 
    "AudioGenerationError"
]
