import asyncio
from pathlib import Path
from typing import List, Optional


def list_speakers(engine: str, language: str) -> List[str]:
    engine_lower = (engine or "").strip().lower()
    try:
        if engine_lower == "melotts":
            from .melotts_service import MeloTTSService
            return MeloTTSService.list_available_speakers(language.upper())
        if engine_lower == "coqui":
            from .coqui_tts_service import CoquiTTSService
            svc = CoquiTTSService(language=language)
            svc._ensure_model()
            return getattr(svc, "_available_speakers", None) or ["(auto)"]
        if engine_lower == "edgetts":
            from .edgetts_service import EdgeTTSService
            svc = EdgeTTSService(language=language)
            return svc.get_available_speakers()
    except Exception:
        pass
    # Google or fallback
    return ["(auto)"]


def synthesize_steps(
    engine: str,
    texts: List[str],
    output_dir: Path,
    *,
    language: str = "en",
    accent: Optional[str] = None,
    speed: float = 1.0,
    emotion: Optional[str] = None,
    sample_rate: int = 24000,
) -> List[Path]:
    engine_lower = (engine or "").strip().lower()

    async def _run() -> List[Path]:
        if engine_lower == "melotts":
            from .melotts_service import MeloTTSService
            tts = MeloTTSService(language=language.upper(), speaker=accent, speed=float(speed), emotion=(emotion or None), sample_rate=int(sample_rate))
            return await tts.synthesize(texts, output_dir)
        if engine_lower == "coqui":
            from .coqui_tts_service import CoquiTTSService
            tts = CoquiTTSService(language=language, speaker=accent, speed=float(speed), emotion=(emotion or None), sample_rate=int(sample_rate))
            return await tts.synthesize(texts, output_dir)
        if engine_lower == "edgetts":
            from .edgetts_service import EdgeTTSService
            tts = EdgeTTSService(language=language, speaker=accent, speed=float(speed), emotion=(emotion or None), sample_rate=int(sample_rate))
            return await tts.synthesize(texts, output_dir)
        # default to Google
        from .google_tts_service import GoogleTTSService
        tts = GoogleTTSService(language=language, tld=(accent or "com"), min_duration=18.0, sample_rate=int(sample_rate))
        return await tts.synthesize(texts, output_dir)

    try:
        return asyncio.run(_run())
    except RuntimeError:
        # Inside existing loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_run())


