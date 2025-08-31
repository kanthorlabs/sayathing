import base64
from typing import Any, Dict
from pydantic import BaseModel, Field, field_serializer, ConfigDict
from enum import Enum

from .kokoro_engine import KokoroVoices, KokoroEngine

class Voices(Enum):
    # Kokoro voices
    KOKORO_AF_HEART = KokoroVoices.AF_HEART.value
    KOKORO_AF_ALLOY = KokoroVoices.AF_ALLOY.value
    KOKORO_AF_AOEDE = KokoroVoices.AF_AOEDE.value
    KOKORO_AF_BELLA = KokoroVoices.AF_BELLA.value
    KOKORO_AF_JESSICA = KokoroVoices.AF_JESSICA.value
    KOKORO_AF_KORE = KokoroVoices.AF_KORE.value
    KOKORO_AF_NICOLE = KokoroVoices.AF_NICOLE.value
    KOKORO_AF_NOVA = KokoroVoices.AF_NOVA.value
    KOKORO_AF_RIVER = KokoroVoices.AF_RIVER.value
    KOKORO_AF_SARAH = KokoroVoices.AF_SARAH.value
    KOKORO_AF_SKY = KokoroVoices.AF_SKY.value
    KOKORO_AM_ADAM = KokoroVoices.AM_ADAM.value
    KOKORO_AM_ECHO = KokoroVoices.AM_ECHO.value
    KOKORO_AM_ERIC = KokoroVoices.AM_ERIC.value
    KOKORO_AM_FENRIR = KokoroVoices.AM_FENRIR.value
    KOKORO_AM_LIAM = KokoroVoices.AM_LIAM.value
    KOKORO_AM_MICHAEL = KokoroVoices.AM_MICHAEL.value
    KOKORO_AM_ONYX = KokoroVoices.AM_ONYX.value
    KOKORO_AM_PUCK = KokoroVoices.AM_PUCK.value
    KOKORO_AM_SANTA = KokoroVoices.AM_SANTA.value
    KOKORO_BF_EMMA = KokoroVoices.BF_EMMA.value
    KOKORO_BF_ISABELLA = KokoroVoices.BF_ISABELLA.value
    KOKORO_BF_ALICE = KokoroVoices.BF_ALICE.value
    KOKORO_BF_LILY = KokoroVoices.BF_LILY.value
    KOKORO_BM_GEORGE = KokoroVoices.BM_GEORGE.value
    KOKORO_BM_LEWIS = KokoroVoices.BM_LEWIS.value
    KOKORO_BM_DANIEL = KokoroVoices.BM_DANIEL.value
    KOKORO_BM_FABLE = KokoroVoices.BM_FABLE.value

class TextToSpeechRequest(BaseModel):
    """
    Represents a request to synthesize text into speech.
    """
    
    text: str
    voice_id: str
    metadata: Dict[str, Any]

    def execute(self) -> 'TextToSpeechResponse':
        engine = Engine.from_voice_id(self.voice_id)
        audio = engine.generate(self.text)
        return TextToSpeechResponse(audio=audio, request=self)

    def to_json(self) -> str:
        """
        Converts a TextToSpeechRequest object into a JSON string.
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_string: str) -> 'TextToSpeechRequest':
        """
        Parses a JSON string into a TextToSpeechRequest object.
        """
        return cls.model_validate_json(json_string)

class TextToSpeechResponse(BaseModel):
    """
    Represents the response from a text-to-speech synthesis.
    """
    audio: bytes

    @field_serializer("audio")
    def encode_audio(self, v: bytes, _info):
        return base64.b64encode(v).decode("utf-8")

    request: TextToSpeechRequest

    def to_json(self) -> str:
        """
        Converts a TextToSpeechResponse object into a JSON string.
        """
        return self.model_dump_json()

class Engine:
    @classmethod
    def from_voice_id(cls, voice_id: str) -> 'Engine':
        return KokoroEngine(voice_id)
