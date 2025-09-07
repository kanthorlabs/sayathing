import base64
import json
import os
from typing import Optional

from pydantic import BaseModel, field_serializer

VOICE_SAMPLE = "A quick fox jumps over the lazy dog."


class VoiceRetrievalError(Exception):
    """Exception raised when voice list retrieval fails"""

    def __init__(self, message: str = "Failed to retrieve voice list"):
        super().__init__(message)


class Voice(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    sample: Optional[bytes] = None

    @field_serializer("sample")
    def serialize_sample(self, value: Optional[bytes]) -> Optional[str]:
        """Serialize bytes to base64 string for JSON serialization"""
        if value is None:
            return None
        return base64.b64encode(value).decode("utf-8")

    @classmethod
    def from_dict(cls, data: dict) -> "Voice":
        return cls(
            id=data["id"],
            name=data["name"],
            language=data["language"],
            gender=data["gender"],
            sample=data.get("sample"),
        )

    @classmethod
    def to_json(cls, voice: "Voice") -> dict:
        return voice.model_dump()


class Voices:
    # Static class variable to store all voices
    _voices: dict = {}

    def __init__(self):
        # Prevent instantiation
        raise RuntimeError("Voices is a static singleton class. Use class methods directly.")

    @classmethod
    def _load_voices(cls) -> dict:
        """Load voice definitions from kokoro_voices.json"""
        if cls._voices is not None:
            return cls._voices

        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "kokoro_voices.json")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                voices_data = json.load(f)

            # Transform the data to add "kokoro." prefix to each voice ID
            transformed_voices = {}
            for voice_id, voice_info in voices_data.items():
                prefixed_id = f"kokoro.{voice_id}"
                transformed_voices[prefixed_id] = voice_info

            cls._voices = transformed_voices
            return cls._voices
        except FileNotFoundError:
            error_msg = f"Voice configuration file not found at {json_path}"
            raise VoiceRetrievalError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing voice configuration file: {e}"
            raise VoiceRetrievalError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error loading voices: {e}"
            raise VoiceRetrievalError(error_msg)

    @classmethod
    def get_all(cls) -> dict:
        """Get all voices data as a dictionary"""
        return cls._load_voices()

    @classmethod
    def get_voice_ids(cls) -> list[str]:
        """Get list of all voice IDs"""
        return list(cls.get_all().keys())

    @classmethod
    def get_voice(cls, voice_id: str) -> dict:
        """Get information for a specific voice"""
        voices_data = cls.get_all()
        return voices_data.get(voice_id, {})

    @classmethod
    def is_valid(cls, voice_id: str) -> bool:
        """Check if a voice ID is valid"""
        return voice_id in cls.get_all()

    @classmethod
    def get_voices_by_language(cls, language: str) -> dict:
        """Get all voices for a specific language"""
        all_voices = cls.get_all()
        return {
            voice_id: voice_data
            for voice_id, voice_data in all_voices.items()
            if voice_data.get("language", "").lower() == language.lower()
        }

    @classmethod
    def get_voices_by_gender(cls, gender: str) -> dict:
        """Get all voices for a specific gender"""
        all_voices = cls.get_all()
        return {
            voice_id: voice_data
            for voice_id, voice_data in all_voices.items()
            if voice_data.get("gender", "").lower() == gender.lower()
        }
