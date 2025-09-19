"""
TTS Services Package

This package provides Text-to-Speech functionality using various engines:
- Google TTS (gTTS)
- Coqui TTS
- MeloTTS
- Edge TTS (Microsoft)
"""

from .base_tts_service import BaseTTSService
from .google_tts_service import GoogleTTSService
from .coqui_tts_service import CoquiTTSService
from .melotts_service import MeloTTSService
from .edgetts_service import EdgeTTSService
from .tts_utils import synthesize_steps, list_speakers

__all__ = [
    "BaseTTSService",
    "GoogleTTSService", 
    "CoquiTTSService",
    "MeloTTSService",
    "EdgeTTSService",
    "synthesize_steps",
    "list_speakers"
]
