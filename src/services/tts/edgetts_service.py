"""
EdgeTTS Service Implementation

This module provides TTS functionality using Microsoft Edge TTS.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import edge_tts
from pydub import AudioSegment
from xml.sax.saxutils import escape as xml_escape

from .base_tts_service import BaseTTSService


class EdgeTTSService(BaseTTSService):
    """TTS using Microsoft Edge TTS with voice selection and SSML support."""

    def __init__(
        self,
        language: str = "en",
        speaker: Optional[str] = None,
        speed: float = 1.0,
        emotion: Optional[str] = None,
        sample_rate: int = 24000,
        voice: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(language, speaker, speed, emotion, sample_rate, **kwargs)
        self.voice = voice or speaker
        self._available_voices: Optional[List[Dict[str, str]]] = None

    def _ensure_voices_loaded(self) -> None:
        """Load available voices if not already loaded."""
        if self._available_voices is None:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._available_voices = loop.run_until_complete(edge_tts.list_voices())
                loop.close()
            except Exception:
                self._available_voices = []

    def _get_voice_for_language(self, language: str) -> Optional[str]:
        """Get the best voice for the given language."""
        self._ensure_voices_loaded()
        if not self._available_voices:
            return None
        
        # Filter voices by language
        lang_voices = [v for v in self._available_voices if v.get('Locale', '').startswith(language)]
        if not lang_voices:
            # Fallback to any voice with similar language code
            lang_voices = [v for v in self._available_voices if language in v.get('Locale', '')]
        
        if not lang_voices:
            return None
        
        # Prefer female voices, then male voices
        female_voices = [v for v in lang_voices if 'Female' in v.get('Gender', '')]
        if female_voices:
            return female_voices[0]['ShortName']
        
        male_voices = [v for v in lang_voices if 'Male' in v.get('Gender', '')]
        if male_voices:
            return male_voices[0]['ShortName']
        
        return lang_voices[0]['ShortName']

    def _resolve_voice(self) -> str:
        """Resolve the voice to use for synthesis."""
        if self.voice:
            return self.voice
        
        # Try to find a voice for the current language
        voice = self._get_voice_for_language(self.language)
        if voice:
            return voice
        
        # Fallback to a default English voice
        return "en-US-AriaNeural"

    def _emotion_to_modifiers(self, emotion: Optional[str]) -> Tuple[float, int]:
        """Map emotion to (rate_factor, pitch_percent)."""
        if not emotion:
            return (1.0, 0)

        e = emotion.strip().lower()
        if e in {"happy", "excited", "cheerful"}:
            return (1.08, +10)
        if e in {"sad", "melancholic"}:
            return (0.95, -10)
        if e in {"angry", "furious"}:
            return (1.05, +5)
        if e in {"calm", "serene"}:
            return (0.98, -5)
        if e in {"serious", "neutral"}:
            return (1.0, 0)
        return (1.0, 0)

    def _create_ssml(self, text: str, voice_name: str) -> str:
        """Create well-formed SSML with explicit voice and prosody.

        - Use percent-based rate/pitch as Azure expects.
        - Escape user text so tags are not spoken.
        """
        emo_rate_factor, emo_pitch_percent = self._emotion_to_modifiers(self.emotion)
        combined_rate = max(0.5, min(2.0, float(self.speed) * emo_rate_factor))
        rate_percent = int(round((combined_rate - 1.0) * 100))
        rate_str = ("+" if rate_percent > 0 else "") + f"{rate_percent}%"
        pitch_str = ("+" if emo_pitch_percent > 0 else "") + f"{emo_pitch_percent}%"

        safe_text = xml_escape(text)
        xml_lang = voice_name.split('-')[0] if '-' in voice_name else (self.language or 'en')

        return (
            f'<speak version="1.0" xml:lang="{xml_lang}">'
            f'<voice name="{voice_name}">'
            f'<prosody rate="{rate_str}" pitch="{pitch_str}">{safe_text}</prosody>'
            f'</voice>'
            f'</speak>'
        )

    async def synthesize(self, texts: List[str], output_dir: Path) -> List[Path]:
        """Synthesize multiple texts to audio files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear existing files
        for file in output_dir.glob("*.wav"):
            file.unlink()
        
        file_paths: List[Path] = []
        for index, text in enumerate(texts, start=1):
            out_path = output_dir / f"step_{index}.wav"
            await self.synthesize_single(text, out_path)
            file_paths.append(out_path)
            await asyncio.sleep(0)  # Yield control
        
        return file_paths

    async def synthesize_single(self, text: str, output_path: Path) -> Path:
        """Synthesize a single text to an audio file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        voice = self._resolve_voice()
        ssml_text = self._create_ssml(text, voice)
        
        # Create temporary file for Edge TTS output
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Generate audio using Edge TTS
            communicate = edge_tts.Communicate(ssml_text, voice)
            await communicate.save(str(temp_path))
            
            # Convert to WAV with proper sample rate
            audio = AudioSegment.from_file(str(temp_path), format="mp3")
            audio = audio.set_frame_rate(self.sample_rate).set_channels(1)
            audio.export(str(output_path), format="wav")
            
        finally:
            # Clean up temporary file
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
        
        return output_path

    def get_available_speakers(self) -> List[str]:
        """Get list of available voices/speakers."""
        self._ensure_voices_loaded()
        if not self._available_voices:
            return ["en-US-AriaNeural"]  # Fallback
        
        # Return short names for easier selection
        return [voice['ShortName'] for voice in self._available_voices]

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        self._ensure_voices_loaded()
        if not self._available_voices:
            return ["en"]  # Fallback
        
        # Extract unique language codes
        languages = set()
        for voice in self._available_voices:
            locale = voice.get('Locale', '')
            if locale:
                lang_code = locale.split('-')[0]
                languages.add(lang_code)
        
        return sorted(list(languages))

    @staticmethod
    async def list_voices() -> List[Dict[str, str]]:
        """List all available voices."""
        try:
            return await edge_tts.list_voices()
        except Exception:
            return []
