"""
Type definitions and constants for the application
"""
import os
from pathlib import Path

class Paths:
    """Path constants for the application"""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent.parent
    AUDIO_STEPS = BASE_DIR / "downloads" / "audio_steps"
    SYNTH_STEPS = BASE_DIR / "downloads" / "synthetic_steps"
    TRANSLATION_STEPS = BASE_DIR / "downloads" / "translation_steps"
    STEP_SCRIPTS = BASE_DIR / "downloads" / "step_scripts"
    DYNAMIC_VOICES = BASE_DIR / "downloads" / "dynamic_voices"
    LOGS = BASE_DIR / "logs"
    TEST_RESULTS = BASE_DIR / "test_results"
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        cls.AUDIO_STEPS.mkdir(parents=True, exist_ok=True)
        cls.SYNTH_STEPS.mkdir(parents=True, exist_ok=True)
        cls.STEP_SCRIPTS.mkdir(parents=True, exist_ok=True)
        cls.DYNAMIC_VOICES.mkdir(parents=True, exist_ok=True)
        cls.LOGS.mkdir(parents=True, exist_ok=True)
        cls.TEST_RESULTS.mkdir(parents=True, exist_ok=True)

class MessageTypes:
    """WebSocket message types"""
    
    # Session management
    SESSION_GREETING = 'session.greeting'
    SESSION_PING = 'session.ping'
    SESSION_DISCONNECT = 'session.disconnect'
    SESSION_OPEN = 'session.open'
    SESSION_CLOSE = 'session.close'
    
    # Response types
    RESPONSE_TEXT = 'response.text'
    RESPONSE_TEXT_DELTA = 'response.text.delta'
    
    # Audio types
    AUDIO_KILL = 'audio.kill'
    AUDIO_DATA = 'audio.data'
    
    # Other types
    SKILL_TRANSFER = 'skill.transfer'
    IDLE_WARNING = 'idle.warning'
    IDLE_TERMINATE = 'idle.terminate'
    TEXT = 'text'
    NO_RESPONSE = 'no_response'
    RAW = 'raw'

class Defaults:
    """Default values for the application"""
    
    # Timeouts and delays
    RESPONSE_TIMEOUT = 60000  # milliseconds (increased from 45s to 60s)
    STEP_DELAY = 5000  # milliseconds (increased from 3s to 5s)
    PING_INTERVAL = 30000  # milliseconds
    CONNECTION_TIMEOUT = 10000  # milliseconds
    BOT_RESPONSE_WAIT = 5000  # milliseconds (increased from 3s to 5s)
    

# Initialize paths
PATHS = Paths()
PATHS.ensure_directories()

DEFAULTS = Defaults()
MESSAGE_TYPES = MessageTypes() 