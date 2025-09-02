from fastapi import APIRouter, status
from tts import TextToSpeechRequest, TextToSpeechResponse

router = APIRouter()

@router.post(
    "/tts", 
    response_model=TextToSpeechResponse,
    tags=["tts"],
    summary="Convert Text to Speech",
    description="Synthesize text into speech using the specified voice",
    response_description="Audio data encoded as base64 along with the original request",
    responses={
        200: {
            "description": "Successfully generated speech audio",
            "content": {
                "application/json": {
                    "example": {
                        "audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqF...",
                        "request": {
                            "text": "Hello, world!",
                            "voice_id": "kokoro.af_heart",
                            "metadata": {}
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid voice_id provided"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during synthesis",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to generate speech audio"
                    }
                }
            }
        }
    }
)
async def text_to_speech(request: TextToSpeechRequest) -> TextToSpeechResponse:
    """
    Convert text to speech using the specified voice.
    
    **Parameters:**
    - **text**: The text to convert to speech (required)
    - **voice_id**: The voice identifier to use for synthesis (required)
    - **metadata**: Additional metadata for the request (optional)
    
    **Voice IDs:**
    Use one of the available voice identifiers. Examples:
    - `kokoro.af_heart` - American Female, warm and friendly
    - `kokoro.am-adam` - American Male, clear and professional
    - `kokoro.bf-emma` - British Female, elegant and refined
    - `kokoro.bm-george` - British Male, authoritative and clear
    
    **Returns:**
    - **audio**: Base64-encoded audio data (WAV format)
    - **request**: Echo of the original request for reference
    
    **Example Usage:**
    ```json
    {
        "text": "Hello, how are you today?",
        "voice_id": "kokoro.af_heart",
        "metadata": {"session_id": "abc123"}
    }
    ```
    """
    
    try:
        response = await request.execute_async()
        return response
    except Exception as e:
        raise
