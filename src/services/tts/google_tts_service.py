import asyncio
from pathlib import Path
from typing import List
from gtts import gTTS
from pydub import AudioSegment

from .base_tts_service import BaseTTSService

class GoogleTTSService(BaseTTSService):
    """Simple TTS using Google gTTS. Outputs WAV PCM with optional min duration."""

    def __init__(self, language: str = "en", tld: str = "com", min_duration: float = 18.0, sample_rate: int = 24000, **kwargs) -> None:
        super().__init__(language=language, sample_rate=sample_rate, **kwargs)
        self.tld = tld
        self.min_duration = min_duration

    async def synthesize(self, texts: List[str], output_dir: Path) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_paths: List[Path] = []

        for index, text in enumerate(texts, start=1):
            out_path = output_dir / f"step_{index}.wav"
            # Generate speech (blocking) in a thread to temporary MP3
            tmp_mp3 = out_path.with_suffix('.mp3')
            # Attempt synthesis with a small retry in case of transient network issues
            attempts_remaining = 2
            last_error: Exception | None = None
            while attempts_remaining > 0:
                try:
                    await asyncio.get_event_loop().run_in_executor(None, self._synthesize_one, text, tmp_mp3)
                    if tmp_mp3.exists():
                        break
                    raise FileNotFoundError(f"Expected temporary MP3 not found: {tmp_mp3}")
                except Exception as error:
                    last_error = error
                    attempts_remaining -= 1
                    if attempts_remaining == 0:
                        raise RuntimeError(
                            f"Failed to synthesize speech to MP3 for step {index}. "
                            f"Original error: {error}. Ensure internet connectivity and that gTTS is reachable."
                        ) from error
            # Post-process to WAV PCM with duration padding
            self._post_process_to_wav(tmp_mp3, out_path)
            # Cleanup temp
            try:
                tmp_mp3.unlink(missing_ok=True)
            except Exception:
                pass
            file_paths.append(out_path)
            await asyncio.sleep(0)
        return file_paths

    async def synthesize_single(self, text: str, output_path: Path) -> Path:
        """Synthesize a single text to a specific output path"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate speech (blocking) in a thread to temporary MP3
        tmp_mp3 = output_path.with_suffix('.mp3')
        attempts_remaining = 2
        last_error: Exception | None = None
        while attempts_remaining > 0:
            try:
                await asyncio.get_event_loop().run_in_executor(None, self._synthesize_one, text, tmp_mp3)
                if tmp_mp3.exists():
                    break
                raise FileNotFoundError(f"Expected temporary MP3 not found: {tmp_mp3}")
            except Exception as error:
                last_error = error
                attempts_remaining -= 1
                if attempts_remaining == 0:
                    raise RuntimeError(
                        f"Failed to synthesize speech to MP3. Original error: {error}. "
                        f"Ensure internet connectivity and that gTTS is reachable."
                    ) from error
        
        # Post-process to WAV PCM with duration padding
        self._post_process_to_wav(tmp_mp3, output_path)
        
        # Cleanup temp
        try:
            tmp_mp3.unlink(missing_ok=True)
        except Exception:
            pass
        
        return output_path

    def _synthesize_one(self, text: str, out_path: Path) -> None:
        tts = gTTS(text=text, lang=self.language, tld=self.tld)
        tts.save(str(out_path))

    def _post_process_to_wav(self, mp3_path: Path, wav_path: Path) -> None:
        # Read MP3 explicitly to avoid format detection pitfalls
        audio = AudioSegment.from_file(str(mp3_path), format="mp3")
        # mono + sample rate
        audio = audio.set_channels(1).set_frame_rate(self.sample_rate)
        # ensure min duration by adding trailing silence
        duration = len(audio) / 1000.0
        if duration < self.min_duration:
            pad_ms = int((self.min_duration - duration) * 1000)
            audio = audio + AudioSegment.silent(duration=pad_ms)
        # Export as 16-bit PCM WAV
        audio.export(
            str(wav_path),
            format="wav",
            parameters=["-acodec", "pcm_s16le", "-ac", "1", "-ar", str(self.sample_rate)]
        )

    def get_available_speakers(self) -> List[str]:
        """Get list of available TLDs/accents for Google TTS."""
        return ["com", "co.uk", "com.au", "ca", "co.in", "ie", "co.za", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh", "ar"]

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for Google TTS."""
        return [
            "af", "ar", "bg", "bn", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "fi", "fr", "gu", "hi", "hr", "hu", "id", "is", "it", "iw", "ja", "jw", "km", "kn", "ko", "la", "lv", "ml", "mr", "my", "ne", "nl", "no", "pl", "pt", "ro", "ru", "si", "sk", "sq", "sr", "su", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "vi", "zh", "zh-cn", "zh-tw"
        ]
