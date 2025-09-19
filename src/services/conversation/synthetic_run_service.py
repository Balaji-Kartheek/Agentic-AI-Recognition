import asyncio
from pathlib import Path
from typing import Dict, List

from src.models.types import PATHS
from src.services.conversation.steps_service import read_steps_file
from src.services.tts import GoogleTTSService, MeloTTSService, CoquiTTSService, EdgeTTSService


class SyntheticRunService:
    """End-to-end helper to generate audio from a steps file using Google TTS."""

    @staticmethod
    async def generate_audio_from_steps_file(
        steps_file: Path,
        engine: str = "google",
        language: str = "en",
        accent: str | None = None,
        speed: float = 1.0,
        emotion: str | None = None,
        sample_rate: int = 24000,
    ) -> Dict:
        try:
            texts: List[str] = read_steps_file(steps_file)
            if not texts:
                return {"success": False, "error": "No steps found in file"}

            engine_lower = (engine or "google").strip().lower()
            if engine_lower in ("coqui", "coqui-tts"):
                tts = CoquiTTSService(language=language, speaker=accent, speed=speed, emotion=emotion, sample_rate=sample_rate)
                output_paths = await tts.synthesize(texts, PATHS.SYNTH_STEPS)
            elif engine_lower == "melo":
                # accent maps to speaker for MeloTTS
                tts = MeloTTSService(language=language.upper(), speaker=accent, speed=speed, emotion=emotion, sample_rate=sample_rate)
                output_paths = await tts.synthesize(texts, PATHS.SYNTH_STEPS)
            elif engine_lower == "edgetts":
                tts = EdgeTTSService(language=language, speaker=accent, speed=speed, emotion=emotion, sample_rate=sample_rate)
                output_paths = await tts.synthesize(texts, PATHS.SYNTH_STEPS)
            else:
                tld = "com" if accent is None else accent
                tts = GoogleTTSService(language=language, tld=tld, min_duration=18.0, sample_rate=sample_rate)
                output_paths = await tts.synthesize(texts, PATHS.SYNTH_STEPS)

            return {
                "success": True,
                "count": len(output_paths),
                "files": [str(p) for p in output_paths]
            }
        except Exception as error:
            return {"success": False, "error": str(error)}


