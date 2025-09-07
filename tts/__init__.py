"""
TTS (Text-to-Speech) module for generating speech from text.

This module provides voice synthesis capabilities using various voice engines.
"""

from .engine_interface import TTSEngineInterface
from .kokoro_engine import (AudioGenerationError, VoiceNotFoundError,
                            VoicePreloadError)
from .tts import Engine, TextToSpeechRequest, TextToSpeechResponse
from .voices import Voice, VoiceRetrievalError, Voices

__all__ = [
    "Voice",
    "Voices",
    "VoiceRetrievalError",
    "Engine",
    "TextToSpeechRequest",
    "TextToSpeechResponse",
    "VoiceNotFoundError",
    "VoicePreloadError",
    "AudioGenerationError",
    "TTSEngineInterface",
]
