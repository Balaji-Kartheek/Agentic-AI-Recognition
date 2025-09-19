import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

from pydub import AudioSegment

from .base_tts_service import BaseTTSService
from ...utils.tts_config import setup_tts_environment

# Setup TTS environment to prevent warnings
setup_tts_environment()


class CoquiTTSService(BaseTTSService):
    """Coqui TTS wrapper with optional prosody adjustments for emotion.

    Notes:
    - Uses Coqui TTS API with a default multi-speaker English model.
    - Emotion is approximated via post-processing (speed/pitch) for broad perceptual effect.
      True emotion control depends on the selected model and may require model-specific params.
    """

    def __init__(
        self,
        language: str = "en",
        speaker: Optional[str] = None,
        speed: float = 1.0,
        emotion: Optional[str] = None,
        sample_rate: int = 24000,
        model_name: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(language, speaker, speed, emotion, sample_rate, **kwargs)
        self.requested_speed = max(0.5, min(2.0, float(speed)))
        self.emotion = (emotion or "").strip() or None
        # Prefer a gruut-based multilingual model to avoid espeak dependency
        # See: https://coqui.ai/docs/tts/models/xtts
        self.model_name = model_name or "tts_models/multilingual/multi-dataset/xtts_v2"
        self._available_speakers: Optional[List[str]] = None

    def _ensure_model(self) -> None:
        if self._model is None:
            try:
                from TTS.api import TTS  # type: ignore
            except Exception as error:
                raise ModuleNotFoundError(
                    "Coqui TTS is not installed. Install via 'pip install TTS' and ensure torch is available."
                ) from error
            self._model = TTS(self.model_name)
            # Detect XTTS environment incompatibility (missing generate) and fall back
            try:
                synthesizer = getattr(self._model, "synthesizer", None)
                tts_model = getattr(synthesizer, "tts_model", None)
                gpt = getattr(tts_model, "gpt", None)
                gpt_infer = getattr(gpt, "gpt_inference", None)
                if gpt_infer is not None and not hasattr(gpt_infer, "generate"):
                    # Switch to a stable single-speaker English model
                    fallback_model = "tts_models/en/ljspeech/tacotron2-DDC"
                    self._model = TTS(fallback_model)
                    self.model_name = fallback_model
                    self._available_speakers = None
            except Exception:
                # If any inspection fails, proceed with current model; runtime will handle retries
                pass
            # Cache speaker list if available (XTTS v2 exposes speakers)
            try:
                spk_list = getattr(self._model, "speakers", None)
                if isinstance(spk_list, list) and spk_list:
                    self._available_speakers = spk_list
                if not self._available_speakers:
                    sm = getattr(self._model, "speaker_manager", None)
                    if sm is not None:
                        sm_speakers = getattr(sm, "speakers", None)
                        if isinstance(sm_speakers, dict) and len(sm_speakers) > 0:
                            self._available_speakers = list(sm_speakers.keys())
            except Exception:
                self._available_speakers = None

    def _resolve_speaker(self) -> Optional[str]:
        # Prefer provided speaker if it exists in model inventory
        if self.speaker:
            if self._available_speakers and self.speaker not in self._available_speakers:
                # Provided speaker not supported by this model, fallback to first
                return self._available_speakers[0] if self._available_speakers else None
            return self.speaker
        # If model provides speakers, choose the first as default
        if self._available_speakers and len(self._available_speakers) > 0:
            return self._available_speakers[0]
        # No safe default speaker id; let the model decide or require speaker_wav
        return None

    @staticmethod
    def _emotion_to_prosody(emotion: Optional[str]) -> Tuple[float, float]:
        """Map emotion to (speed_factor, pitch_semitones)."""
        if not emotion:
            return (1.0, 0.0)
        e = emotion.strip().lower()
        if e in {"happy", "excited", "cheerful"}:
            return (1.10, +2.0)
        if e in {"sad", "melancholic"}:
            return (0.95, -2.0)
        if e in {"angry", "furious"}:
            return (1.12, +1.0)
        if e in {"calm", "serene"}:
            return (0.98, -1.0)
        if e in {"serious", "neutral"}:
            return (1.0, 0.0)
        return (1.0, 0.0)

    @staticmethod
    def _change_pitch(audio: AudioSegment, semitones: float) -> AudioSegment:
        if abs(semitones) < 1e-6:
            return audio
        # Changing pitch by altering frame rate, then resetting to target sample rate.
        new_frame_rate = int(audio.frame_rate * (2.0 ** (semitones / 12.0)))
        shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
        return shifted.set_frame_rate(audio.frame_rate)

    @staticmethod
    def _change_speed(audio: AudioSegment, speed: float) -> AudioSegment:
        if abs(speed - 1.0) < 1e-6:
            return audio
        # Speed change by resampling via frame rate hack
        new_frame_rate = int(audio.frame_rate * speed)
        sped = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
        return sped.set_frame_rate(audio.frame_rate)

    async def synthesize(self, texts: List[str], output_dir: Path) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear existing files
        for file in output_dir.glob("*.wav"):
            file.unlink()
            
        file_paths: List[Path] = []
        for index, text in enumerate(texts, start=1):
            out_path = output_dir / f"step_{index}.wav"
            await self.synthesize_single(text, out_path)
            file_paths.append(out_path)
            await asyncio.sleep(0)
        return file_paths

    async def synthesize_single(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.get_event_loop().run_in_executor(None, self._synthesize_blocking, text, output_path)
        return output_path

    def _synthesize_blocking(self, text: str, output_path: Path) -> None:
        self._ensure_model()

        temp_raw = output_path.with_suffix(".rawgen.wav")

        # Some models accept speaker as a string; others use speaker_id or speaker_wav.
        kwargs = {
            "text": text,
            "file_path": str(temp_raw),
        }

        # Language is not used by all models; pass if accepted for multilingual models only.
        if self.language and "multilingual" in (self.model_name or ""):
            kwargs["language"] = self.language

        speaker_name = self._resolve_speaker()
        if speaker_name:
            kwargs["speaker"] = speaker_name
        else:
            # Fallback to a bundled reference wav for XTTS-like models
            try:
                default_ref_wav = (Path(__file__).parent / "output" / "CoquiTTS" / "voice.wav").resolve()
                if default_ref_wav.exists():
                    kwargs["speaker_wav"] = str(default_ref_wav)
            except Exception:
                pass

        try:
            # Try with potential parameters; Coqui TTS will ignore unknowns or may raise.
            self._model.tts_to_file(**kwargs)
        except (TypeError, KeyError, ValueError):
            # If failure due to missing/invalid speaker, try with reference wav only
            ref_wav = (Path(__file__).parent / "output" / "CoquiTTS" / "voice.wav").resolve()
            try:
                if ref_wav.exists():
                    self._model.tts_to_file(text=text, file_path=str(temp_raw), language=self.language, speaker_wav=str(ref_wav))
                else:
                    # Retry without optional params that may cause issues (speaker/language)
                    self._model.tts_to_file(text=text, file_path=str(temp_raw))
            except Exception:
                # Final minimal retry
                self._model.tts_to_file(text=text, file_path=str(temp_raw))

        # Load and apply prosody adjustments
        audio = AudioSegment.from_file(temp_raw)
        audio = audio.set_frame_rate(self.sample_rate).set_channels(1)

        # Combine requested speed with emotion mapping
        emo_speed, emo_pitch = self._emotion_to_prosody(self.emotion)
        combined_speed = max(0.5, min(2.0, self.requested_speed * emo_speed))

        if abs(emo_pitch) > 1e-6:
            audio = self._change_pitch(audio, emo_pitch)
        if abs(combined_speed - 1.0) > 1e-6:
            audio = self._change_speed(audio, combined_speed)

        audio.export(output_path, format="wav")
        try:
            temp_raw.unlink(missing_ok=True)
        except Exception:
            pass

    def get_available_speakers(self) -> List[str]:
        """Get list of available speakers for Coqui TTS."""
        if self._available_speakers:
            return self._available_speakers
        return ["(auto)"]

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for Coqui TTS."""
        return [
            "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "ko", "hi", "th", "vi", "uk", "ca", "fi", "hu", "ro", "sk", "sl", "hr", "bg", "el", "et", "lv", "lt", "mt", "da", "sv", "no", "is", "ga", "cy", "eu", "af", "sq", "az", "be", "bn", "bs", "br", "my", "km", "co", "eo", "fo", "gl", "ka", "gu", "ha", "haw", "iw", "ig", "id", "ga", "jv", "kn", "kk", "ky", "lo", "la", "lb", "mk", "mg", "ms", "ml", "mi", "mr", "mn", "ne", "ny", "ps", "fa", "pa", "sm", "gd", "sr", "st", "sn", "sd", "si", "so", "su", "sw", "tg", "ta", "tt", "te", "to", "ur", "uz", "xh", "yi", "yo", "zu"
        ]


