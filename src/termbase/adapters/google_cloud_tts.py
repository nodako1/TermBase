from __future__ import annotations

import os
from importlib import import_module
from pathlib import Path

from termbase.errors import AudioGenerationError


class GoogleCloudTTSClient:
    def __init__(
        self,
        credentials_path: Path,
        language_code: str,
        audio_encoding: str,
    ) -> None:
        self.credentials_path = credentials_path
        self.language_code = language_code
        self.audio_encoding = audio_encoding

    def synthesize(
        self,
        text: str,
        voice_name: str,
        speaking_rate: float,
        pitch_semitones: float,
        use_ssml: bool,
    ) -> bytes:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(self.credentials_path)
        try:
            texttospeech = import_module("google.cloud.texttospeech")
            client = texttospeech.TextToSpeechClient()
            response = client.synthesize_speech(
                request={
                    "input": self._build_synthesis_input(texttospeech, text, use_ssml),
                    "voice": texttospeech.VoiceSelectionParams(
                        language_code=self.language_code,
                        name=voice_name,
                    ),
                    "audio_config": texttospeech.AudioConfig(
                        audio_encoding=self._resolve_audio_encoding(texttospeech),
                        speaking_rate=speaking_rate,
                        pitch=pitch_semitones,
                    ),
                }
            )
        except Exception as exc:
            raise AudioGenerationError(f"google cloud tts request failed: {exc}") from exc
        return response.audio_content

    def _build_synthesis_input(self, texttospeech, text: str, use_ssml: bool):
        if use_ssml:
            return texttospeech.SynthesisInput(ssml=text)
        return texttospeech.SynthesisInput(text=text)

    def _resolve_audio_encoding(self, texttospeech):
        if self.audio_encoding == "linear16":
            return texttospeech.AudioEncoding.LINEAR16
        return texttospeech.AudioEncoding.MP3