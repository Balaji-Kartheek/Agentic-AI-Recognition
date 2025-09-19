"""
TTS Configuration and Environment Setup

This module handles TTS-related environment configuration to prevent
common warnings and issues.
"""

import os
import warnings


def setup_tts_environment():
    """Set up environment variables for TTS services to prevent warnings."""
    
    # Disable tokenizers parallelism to avoid fork warnings
    # This prevents the warning: "The current process just got forked, after parallelism has already been used"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # Suppress specific warnings that are common with TTS libraries
    warnings.filterwarnings("ignore", message=".*tokenizers.*")
    warnings.filterwarnings("ignore", message=".*fork.*")
    
    # Set optimal threading settings for TTS operations
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    
    # Disable CUDA warnings if not using GPU
    os.environ["CUDA_VISIBLE_DEVICES"] = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    
    print("✅ TTS environment configured successfully")


def get_tts_environment_info():
    """Get information about the current TTS environment configuration."""
    return {
        "TOKENIZERS_PARALLELISM": os.environ.get("TOKENIZERS_PARALLELISM", "not set"),
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "not set"),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", "not set"),
        "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", "not set"),
    }


# Auto-setup when module is imported
setup_tts_environment()
