from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional, Tuple


LANGUAGE_TO_SPEECH = {
    "en": ("en-US", []),
    "hi": ("hi-IN", []),
    "hinglish": ("hi-IN", ["en-IN"]),
}

LANGUAGE_TO_TTS = {
    "en": ("en-US", "en-US-Neural2-F"),
    "hi": ("hi-IN", "hi-IN-Wavenet-A"),
    "hinglish": ("en-IN", "en-IN-Wavenet-A"),
}


@dataclass(frozen=True)
class VoiceRuntimeStatus:
    speech_to_text: bool
    text_to_speech: bool
    provider: str = "google_cloud"

    @property
    def enabled(self) -> bool:
        return self.speech_to_text and self.text_to_speech


def detect_voice_runtime() -> VoiceRuntimeStatus:
    explicit_flag = os.getenv("MANOVARTA_ENABLE_CLOUD_VOICE")
    if explicit_flag is not None and explicit_flag.strip().lower() not in {"1", "true", "yes", "on"}:
        return VoiceRuntimeStatus(speech_to_text=False, text_to_speech=False)
    if explicit_flag is None and not (os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_PROJECT")):
        return VoiceRuntimeStatus(speech_to_text=False, text_to_speech=False)
    try:
        from google.cloud import speech, texttospeech  # noqa: F401
    except Exception:
        return VoiceRuntimeStatus(speech_to_text=False, text_to_speech=False)
    return VoiceRuntimeStatus(speech_to_text=True, text_to_speech=True)


def transcribe_audio(content: bytes, language: str, mime_type: str = "audio/webm") -> str:
    if not content:
        return ""

    try:
        from google.cloud import speech
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("google-cloud-speech is not installed") from exc

    primary, alternatives = LANGUAGE_TO_SPEECH.get(language, LANGUAGE_TO_SPEECH["en"])
    encoding = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    if "ogg" in mime_type:
        encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS
    elif "wav" in mime_type:
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=encoding,
        language_code=primary,
        alternative_language_codes=alternatives,
        enable_automatic_punctuation=True,
        model="latest_long",
    )
    response = client.recognize(config=config, audio=audio)
    transcript_bits = [
        result.alternatives[0].transcript.strip()
        for result in response.results
        if result.alternatives and result.alternatives[0].transcript.strip()
    ]
    return " ".join(transcript_bits).strip()


def synthesize_speech(text: str, language: str) -> Tuple[bytes, str]:
    if not text.strip():
        return b"", "audio/mpeg"

    try:
        from google.cloud import texttospeech
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("google-cloud-texttospeech is not installed") from exc

    language_code, voice_name = LANGUAGE_TO_TTS.get(language, LANGUAGE_TO_TTS["en"])
    client = texttospeech.TextToSpeechClient()
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
        ),
    )
    return response.audio_content, "audio/mpeg"
