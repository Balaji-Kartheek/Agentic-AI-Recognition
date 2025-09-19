import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from .base_tts_service import BaseTTSService
from ...utils.tts_config import setup_tts_environment

# Setup TTS environment to prevent warnings
setup_tts_environment()


class MeloTTSService(BaseTTSService):
    """TTS using MeloTTS. Writes WAV directly with configurable speaker and speed."""

    def __init__(
        self,
        language: str = "EN",
        speaker: Optional[str] = None,
        speed: float = 1.0,
        emotion: Optional[str] = None,
        sample_rate: int = 24000,
        **kwargs
    ) -> None:
        super().__init__(language, speaker, speed, emotion, sample_rate, **kwargs)
        self.speed = max(0.5, min(2.0, float(speed)))
        self.emotion = emotion  # Placeholder; MeloTTS may not consume this directly
        # Lazy model init in background thread-safe manner
        self._speaker_name = speaker
        self._speaker_map: Optional[Dict[str, int]] = None

    def _ensure_model(self) -> None:
        if self._model is None:
            try:
                from melo.api import TTS as MeloTTS  # type: ignore
            except Exception as error:
                raise ModuleNotFoundError(
                    "MeloTTS is not installed. Install via 'pip install git+https://github.com/myshell-ai/MeloTTS.git' "
                    "and ensure dependencies like torch are installed."
                ) from error
            self._model = MeloTTS(language=self.language, device='auto')
            # Build speaker name -> id map once
            try:
                self._speaker_map = dict(self._model.hps.data.spk2id)
            except Exception:
                self._speaker_map = None

    def _resolve_speaker_id(self) -> int:
        # Try to map provided speaker name to id; fallback to first available
        if self._speaker_map and self._speaker_name and self._speaker_name in self._speaker_map:
            return int(self._speaker_map[self._speaker_name])
        if self._speaker_map and len(self._speaker_map) > 0:
            # Prefer EN-Default style names if available
            for preferred in ["EN-Default", "EN_DEFAULT", "EN", "default"]:
                if preferred in self._speaker_map:
                    return int(self._speaker_map[preferred])
            # Otherwise first item
            return int(next(iter(self._speaker_map.values())))
        # Fallback speaker id 0
        return 0

    async def synthesize(self, texts: List[str], output_dir: Path) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_paths: List[Path] = []
        
        
        #clear the existing files
        for file in output_dir.glob("*.wav"):
            file.unlink()

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
        speaker_id = self._resolve_speaker_id()
        # MeloTTS writes WAV directly; speed supported. Emotion currently unused.
        self._model.tts_to_file(text, speaker_id, str(output_path), speed=float(self.speed))

    @staticmethod
    def list_available_speakers(language: str = "EN") -> List[str]:
        try:
            from melo.api import TTS as MeloTTS  # type: ignore
            model = MeloTTS(language=language, device='auto')
            spk2id = getattr(model.hps.data, 'spk2id', None)
            if isinstance(spk2id, dict):
                return list(spk2id.keys())
        except Exception:
            pass
        # Conservative defaults commonly present in MeloTTS EN pack
        return ["EN-Default", "EN-US", "EN-AU", "EN-BR", "EN_INDIA"]

    def get_available_speakers(self) -> List[str]:
        """Get list of available speakers for MeloTTS."""
        return self.list_available_speakers(self.language)

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for MeloTTS."""
        return ["EN", "ES", "FR", "DE", "IT", "PT", "PL", "RU", "JA", "KR", "ZH"]


