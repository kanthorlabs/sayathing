from kokoro import KPipeline
import soundfile as sf
import torch
import base64
import io
from enum import Enum

class KokoroVoices(Enum):
    # American English Female Voices
    AF_HEART = "kokoro.af_heart"           # Heart - ❤️ - Grade: A
    AF_ALLOY = "kokoro.af_alloy"           # Alloy - Grade: C
    AF_AOEDE = "kokoro.af_aoede"           # Aoede - Grade: C+
    AF_BELLA = "kokoro.af_bella"           # Bella - 🔥 - Grade: A-
    AF_JESSICA = "kokoro.af_jessica"       # Jessica - Grade: D
    AF_KORE = "kokoro.af_kore"             # Kore - Grade: C+
    AF_NICOLE = "kokoro.af_nicole"         # Nicole - 🎧 - Grade: B-
    AF_NOVA = "kokoro.af_nova"             # Nova - Grade: C
    AF_RIVER = "kokoro.af_river"           # River - Grade: D
    AF_SARAH = "kokoro.af_sarah"           # Sarah - Grade: C+
    AF_SKY = "kokoro.af_sky"               # Sky - Grade: C-
    
    # American English Male Voices
    AM_ADAM = "kokoro.am_adam"             # Adam - Grade: F+
    AM_ECHO = "kokoro.am_echo"             # Echo - Grade: D
    AM_ERIC = "kokoro.am_eric"             # Eric - Grade: D
    AM_FENRIR = "kokoro.am_fenrir"         # Fenrir - Grade: C+
    AM_LIAM = "kokoro.am_liam"             # Liam - Grade: D
    AM_MICHAEL = "kokoro.am_michael"       # Michael - Grade: C+
    AM_ONYX = "kokoro.am_onyx"             # Onyx - Grade: D
    AM_PUCK = "kokoro.am_puck"             # Puck - Grade: C+
    AM_SANTA = "kokoro.am_santa"           # Santa - Grade: D-
    
    # British English Female Voices
    BF_EMMA = "kokoro.bf_emma"             # Emma - 🚺 - Grade: B-
    BF_ISABELLA = "kokoro.bf_isabella"     # Isabella - Grade: C
    BF_ALICE = "kokoro.bf_alice"           # Alice - 🚺 - Grade: D
    BF_LILY = "kokoro.bf_lily"             # Lily - 🚺 - Grade: D
    
    # British English Male Voices
    BM_GEORGE = "kokoro.bm_george"         # George - Grade: C
    BM_LEWIS = "kokoro.bm_lewis"           # Lewis - Grade: D+
    BM_DANIEL = "kokoro.bm_daniel"         # Daniel - 🚹 - Grade: D
    BM_FABLE = "kokoro.bm_fable"           # Fable - 🚹 - Grade: C


class KokoroEngine:
    def __init__(self, voice_id: str):
        # Validate voice_id is in KokoroVoices enum
        if voice_id not in [voice.value for voice in KokoroVoices]:
            raise ValueError(f"Invalid voice_id '{voice_id}'. Must be one of: {[voice.value for voice in KokoroVoices]}")
        
        self.pipeline = KPipeline(repo_id='hexgrad/Kokoro-82M', lang_code='a')
        self.voice_id = voice_id
        self.sampling_rate = 24000

    def generate(self, text: str) -> bytes:
        voice_id = self.voice_id.split(".")[1] if self.voice_id else self.voice_id
        generator = self.pipeline(text, voice=voice_id)
        [result] = list(generator)
        
        buffer = io.BytesIO()
        sf.write(buffer, result.audio, self.sampling_rate, format='WAV')
        buffer.seek(0)
        return buffer.read()

