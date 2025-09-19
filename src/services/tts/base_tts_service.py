"""
Base TTS Service Interface

This module provides the base interface that all TTS services should implement
to ensure consistency across different TTS engines.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any


class BaseTTSService(ABC):
    """Base interface for all TTS services."""
    
    def __init__(
        self,
        language: str = "en",
        speaker: Optional[str] = None,
        speed: float = 1.0,
        emotion: Optional[str] = None,
        sample_rate: int = 24000,
        **kwargs
    ) -> None:
        self.language = language
        self.speaker = speaker
        self.speed = max(0.5, min(2.0, float(speed)))
        self.emotion = emotion
        self.sample_rate = sample_rate
        self._model = None
    
    @abstractmethod
    async def synthesize(self, texts: List[str], output_dir: Path) -> List[Path]:
        """
        Synthesize multiple texts to audio files.
        
        Args:
            texts: List of text strings to synthesize
            output_dir: Directory to save the audio files
            
        Returns:
            List of paths to generated audio files
        """
        pass
    
    @abstractmethod
    async def synthesize_single(self, text: str, output_path: Path) -> Path:
        """
        Synthesize a single text to an audio file.
        
        Args:
            text: Text string to synthesize
            output_path: Path where to save the audio file
            
        Returns:
            Path to the generated audio file
        """
        pass
    
    @abstractmethod
    def get_available_speakers(self) -> List[str]:
        """
        Get list of available speakers for this TTS service.
        
        Returns:
            List of speaker names/IDs
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported languages for this TTS service.
        
        Returns:
            List of language codes
        """
        pass
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about this TTS service.
        
        Returns:
            Dictionary with service information
        """
        return {
            "service_name": self.__class__.__name__,
            "language": self.language,
            "speaker": self.speaker,
            "speed": self.speed,
            "emotion": self.emotion,
            "sample_rate": self.sample_rate,
            "available_speakers": self.get_available_speakers(),
            "supported_languages": self.get_supported_languages()
        }
