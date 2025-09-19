"""
Configuration module for Avaamo Agentic Audio Evaluator
"""
import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the application"""
    
    def __init__(self):
        # API Configuration"
        self.access_token = "sz1wyFXDa-NCrqck3AG1p9O1FNGUTEdf"
        self.device_id = "12345667"
        
        # Conversation Configuration
        # List of conversation UUIDs to process
        self.conversation_ids = [
            "75dd49b5dd6f706e8ec7772e24a23e4f",
            "a75f4ec64775686673384db31e43b99e"
        ]
        
        # For backward compatibility, keep the first one as default
        self.conversation_id = self.conversation_ids[0]
        
        # Web Channel Configuration (Channel UUID)
        self.channel_id = "a041fb81-0a49-4a89-a5ef-b1b5af2d9a35"
        
        # API Endpoints
        self.base_url = "https://c6.avaamo.com"
        
        # Web Socket Connection Endpoint
        self.ws_url = "wss://c6.avaamo.com/promptws"
        
        # Conversation Mode
        self.conversation_mode = "voice"
        # Run type: human | synthetic | translation | dynamic
        self.run_type = "human"
        
        # Request timeout (in milliseconds)
        self.timeout = 30000
        
        # OpenAI Configuration
        # Prefer Streamlit secrets; fall back to environment variable
        self.openai_api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4o')

        # Synthetic run configuration
        # When true, the evaluator will skip fetching/downloading and use provided files/texts
        self.synthetic_mode = False
        # Absolute file paths to pre-generated audio files (e.g., in downloads/synthetic_steps)
        self.synthetic_files = []
        # Utterance texts aligned with synthetic_files (same length); if shorter, blanks will be used
        self.synthetic_texts = []

        # Dynamic Synthetic run configuration
        # When true, run dynamically using LLM-generated utterances and TTS per turn
        self.dynamic_synthetic_mode = False
        # Scenario description to seed the conversation (e.g., "Confirm the Appointment")
        self.dynamic_scenario = "Confirm the appointment"
        # Maximum number of user turns to perform
        self.dynamic_max_steps = 6
        # Temperature for LLM generation of next utterance
        self.dynamic_temperature = '0.3'

# Create global config instance
config = Config() 