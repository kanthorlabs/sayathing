import logging
import asyncio
from fastapi import APIRouter, Query
from tts import Engine, Voices, Voice

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/tts/voices",
    response_model=list[Voice],
    tags=["voices"],
    summary="List Available Voices",
    description="Get a list of all available voices for text-to-speech synthesis",
    response_description="List of available voices with their metadata",
    responses={
        200: {
            "description": "Successfully retrieved voice list",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "kokoro.af_heart",
                            "name": "Heart",
                            "language": "en-us",
                            "gender": "Female",
                        },
                        {
                            "id": "kokoro.am_adam",
                            "name": "Adam", 
                            "language": "en-us",
                            "gender": "Male",
                        }
                    ]
                }
            }
        }
    }
)
async def list_voices(
    include_samples: bool = Query(
        default=False,
        description="Whether to include audio samples for each voice. Setting to true will increase response size and time."
    )
) -> list[Voice]:
    """
    Get a list of all available voices for text-to-speech synthesis.
    
    Returns detailed information about each voice including:
    - **id**: The voice identifier to use in TTS requests (with kokoro. prefix)
    - **name**: Human-readable name of the voice
    - **language**: Language code (e.g., en-us, en-gb)
    - **gender**: Voice gender (Male/Female)
    - **sample**: Base64-encoded audio sample (only included if include_samples=true)
    
    Use the `id` field when making requests to the `/tts` endpoint.
    
    Args:
        include_samples: Whether to include audio samples for each voice (default: False).
                        Setting to True will increase response size and processing time.
    """

    logger.info(f"Listing voices (include_samples: {include_samples})")
    
    try:
        voices = Voices.get_all()
        items = []
        
        if include_samples:
            logger.info("Processing voice samples concurrently...")
            
            # Create semaphore to limit concurrent operations
            try:
                from server.config.async_config import AsyncConfig
                max_concurrent = AsyncConfig.MAX_CONCURRENT_VOICE_SAMPLES
            except ImportError:
                max_concurrent = 10  # Default
            
            semaphore = asyncio.Semaphore(max_concurrent)
            
            # Process samples concurrently for better performance
            async def process_voice_with_sample(voice_id: str, voice_data: dict):
                async with semaphore:  # Limit concurrent operations
                    item = Voice.from_dict({**voice_data, "id": voice_id})
                    item.sample = await Engine.get_sample_async(voice_id)
                    return item
            
            # Create tasks for concurrent processing
            tasks = [
                process_voice_with_sample(voice_id, voice_data)
                for voice_id, voice_data in voices.items()
            ]
            
            # Wait for all tasks to complete
            items = await asyncio.gather(*tasks)
            logger.info(f"Successfully processed {len(items)} voice samples")
        else:
            # No samples needed, process synchronously (faster)
            for voice_id, voice in voices.items():
                item = Voice.from_dict({**voice, "id": voice_id})
                items.append(item)
            logger.info(f"Successfully processed {len(items)} voices")

        sorted_voices = sorted(items, key=lambda x: (x.language, x.gender, x.name))
        return sorted_voices
        
    except Exception as e:
        logger.error(f"Failed to list voices: {str(e)}")
        raise
