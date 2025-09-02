"""
Abstract interface for TTS engines.

This module defines the abstract base class that all TTS engines must implement
to ensure consistency and proper method signatures across different engine implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional


class TTSEngineInterface(ABC):
    """
    Abstract base class defining the interface that all TTS engines must implement.
    
    This interface ensures that all engines provide the necessary methods for:
    - Asynchronous text-to-speech generation
    - Voice sample retrieval
    - Engine preloading for performance optimization
    - Proper shutdown and cleanup
    """

    @abstractmethod
    async def generate_async(self, text: str, voice_id: str) -> bytes:
        """
        Generate speech audio from text asynchronously.
        
        Args:
            text: The text to convert to speech
            voice_id: The voice identifier to use for synthesis
            
        Returns:
            bytes: The generated audio data in WAV format
            
        Raises:
            VoiceNotFoundError: If the voice_id is not available
            AudioGenerationError: If audio generation fails
        """
        pass

    @classmethod
    @abstractmethod
    async def get_sample_async(cls, voice_id: str) -> Optional[bytes]:
        """
        Get a sample audio for the specified voice asynchronously.
        
        Args:
            voice_id: The voice identifier to get a sample for
            
        Returns:
            Optional[bytes]: The sample audio data in WAV format, or None if unavailable
        """
        pass

    @classmethod
    @abstractmethod
    async def preload_async(cls) -> None:
        """
        Preload the engine and its resources asynchronously for better performance.
        
        This method should prepare voices, models, and other resources that can be
        loaded ahead of time to reduce latency during actual generation.
        """
        pass

    @classmethod
    @abstractmethod
    def get_instance(cls) -> 'TTSEngineInterface':
        """
        Get the singleton instance of the engine.
        
        Returns:
            TTSEngineInterface: The engine instance
        """
        pass

    @classmethod
    @abstractmethod
    def shutdown(cls) -> None:
        """
        Shutdown the engine and cleanup all resources.
        
        This method should properly close thread pools, clear caches,
        and perform any other necessary cleanup operations.
        """
        pass
