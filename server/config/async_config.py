"""
Async configuration settings for the TTS service.
These settings control the performance characteristics of async operations.
"""

import os
from typing import Optional

class AsyncConfig:
    """Configuration for async TTS operations"""
    
    # Thread pool settings for CPU-bound TTS operations
    TTS_THREAD_POOL_MAX_WORKERS: int = int(os.getenv("TTS_THREAD_POOL_MAX_WORKERS", "4"))
    
    # Timeout settings
    TTS_GENERATION_TIMEOUT: float = float(os.getenv("TTS_GENERATION_TIMEOUT", "30.0"))
    VOICE_PRELOAD_TIMEOUT: float = float(os.getenv("VOICE_PRELOAD_TIMEOUT", "120.0"))
    
    # Batch processing settings
    MAX_CONCURRENT_VOICE_SAMPLES: int = int(os.getenv("MAX_CONCURRENT_VOICE_SAMPLES", "10"))
    
    @classmethod
    def get_tts_executor_config(cls) -> dict:
        """Get configuration for TTS thread pool executor"""
        return {
            "max_workers": cls.TTS_THREAD_POOL_MAX_WORKERS,
            "thread_name_prefix": "sayathing-tts-async"
        }
