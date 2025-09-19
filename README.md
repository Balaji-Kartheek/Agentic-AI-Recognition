# AgenticAI Suite - Comprehensive Information Guide

## 🎯 Overview

The **AgenticAI Suite** is a sophisticated Python-based testing framework designed to evaluate conversational AI bots (specifically Avaamo bots) through automated audio conversation testing. The system simulates real user interactions by sending pre-recorded audio files through WebSocket connections and evaluates the bot's responses using OpenAI's LLM models.

## 🏗️ Architecture Overview

### Service Architecture
- **SessionService**: Manages WebSocket session creation
- **WebSocketService**: Handles real-time communication
- **DownloadService**: Manages audio file downloads
- **AudioService**: Processes and sends audio files
- **OpenAIService**: LLM-based conversation evaluation
- **TestResultsService**: Test result management and storage

## 🚀 Execution Flow

### 1. **Session Creation** (`SessionService.create_session`)
```python
# Creates WebSocket session for agentic agents
POST https://x1.avaamo.com/web_channel/channel/{channel_id}/agentic_agents/create_session
```

**Parameters(User Payload):**
- `channel_id`: Avaamo channel UUID
- `user.name`: "User"
- `user.phone`: "9876543210"
- `user.email`: "qabot@avaamo.com"

**Response:**
- Session token for WebSocket connection
- Channel information
- Session metadata

### 2. **Conversation Data Fetching** (`SessionService.fetch_conversation`)
```python
# Fetches conversation transcript and audio from Avaamo API
GET {base_url}/conversations/{conversation_id}/messages.json
```

**Headers:**
- `Access-Token`: Your Avaamo access token
- `Device-Id`: Device identifier
- `Content-Type`: application/json

**Response Processing:**
- Extracts full call recording
- Parses conversation transcript
- Identifies user audio segments
- Builds step-by-step audio mapping

### 3. **Audio File Download** (`DownloadService.download_all_step_audio`)
**Process:**
- Downloads each audio segment to `downloads/audio_steps/`
- Files named: `step_1.mp3`, `step_2.mp3`, etc.
- Validates download success and file integrity
- Tracks download progress and errors

### 4. **WebSocket Connection** (`WebSocketService.create_connection`)
**Connection Details:**
- URL: `wss://x1.avaamo.com/promptws?jst={token}&mode=voice`
- Establishes real-time bidirectional communication
- Sends session greeting message
- Maintains connection with ping intervals

### 5. **Audio File Transmission** (`AudioService.send_all_audio_files_sequentially`)
**Execution Flow:**
1. Waits for bot's initial greeting
2. Sends audio files sequentially with delays
3. Logs each interaction to conversation history
4. Tracks bot responses and timing
5. Handles connection errors and timeouts

### 6. **LLM Evaluation** (`OpenAIService.evaluate_conversation`)
**Evaluation Process:**
- Compares actual conversation with golden transcript
- Uses GPT-4o (or configured model) for analysis
- Generates pass/fail results with detailed feedback
- Provides improvement recommendations

### 7. **Result Storage** (`TestResultsService.save_test_result`)
**Storage:**
- Saves test results as JSON files
- Generates unique test IDs with timestamps
- Stores in `test_results/` directory
- Includes metadata and evaluation details

## ⚙️ Configuration Parameters

### Environment Variables (`.env` file)
```bash
# Required: Avaamo API Access
AGENT_ACCESS_TOKEN=your_avaamo_access_token_here

# Required: OpenAI API for evaluation
OPENAI_API_KEY=your_openai_api_key_here

# Optional: LLM Model selection
LLM_MODEL=gpt-4o
```

### Configuration Class (`config/config.py`)
```python
class Config:
    # API Configuration
    access_token = os.getenv('AGENT_ACCESS_TOKEN')
    device_id = "12345667"
    
    # Conversation Configuration
    conversation_id = "7d2f577843761d41a6cf290b6702995e"
    
    # Web Channel Configuration
    channel_id = "38966ae1-e876-41d2-9ea9-18ceafc7015f"
    
    # API Endpoints
    base_url = "https://x1.avaamo.com/"
    
    # Request timeout (milliseconds)
    timeout = 30000
    
    # OpenAI Configuration
    openai_api_key = os.getenv('OPENAI_API_KEY')
    llm_model = os.getenv('LLM_MODEL', 'gpt-4o')
```

### Default Values (`src/models/types.py`)
```python
class Defaults:
    # Timeouts and delays
    RESPONSE_TIMEOUT = 45000      # 45 seconds
    STEP_DELAY = 3000            # 3 seconds between steps
    PING_INTERVAL = 30000        # 30 seconds ping
    CONNECTION_TIMEOUT = 10000   # 10 seconds connection timeout
    BOT_RESPONSE_WAIT = 3000    # 3 seconds bot response wait
    
```

## 📁 File Structure & Locations

### Directory Structure
```
AgenticAI/
├── config/
│   └── config.py                    # Configuration management
├── src/
│   ├── services/                    # Core services
│   │   ├── conversation/            # Conversation flow & orchestration
│   │   │   ├── session_service.py
│   │   │   ├── audio_service.py
│   │   │   ├── steps_service.py
│   │   │   ├── dynamic_run_service.py
│   │   │   └── synthetic_run_service.py
│   │   ├── websocket/               # WebSocket handling
│   │   │   └── websocket_service.py
│   │   ├── io/                      # File I/O and persistence
│   │   │   ├── download_service.py
│   │   │   └── test_results_service.py
│   │   ├── evaluation/              # Evaluation and reporting
│   │   │   ├── openai_service.py
│   │   │   └── html_report_service.py
│   │   └── tts/                     # Text-to-Speech engines & helpers
│   │       ├── google_tts_service.py
│   │       ├── melotts_service.py
│   │       ├── coqui_tts_service.py
│   │       └── tts_utils.py
│   ├── models/
│   │   └── types.py                 # Data models & constants
│   ├── utils/
│   │   ├── logger.py                # Logging utilities
│   │   └── conversation.py          # Conversation processing
│   └── app.py                       # Main application
├── downloads/
│   └── audio_steps/                 # Downloaded audio files
├── logs/                             # Conversation logs
├── test_results/                     # Test evaluation results
├── main.py                           # Entry point
├── run.py                            # Alternative runner
└── test_suite.py                     # Test validation script
```

### File Naming Conventions
- **Audio Files**: `step_1.mp3`, `step_2.mp3`, etc.
- **Log Files**: `conversation_history_{conversation_id}_{timestamp}.txt`
- **Test Results**: `test_result_{conversation_id}_{timestamp}.json`
- **Configuration**: `.env` (environment variables)

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Avaamo API access token
- OpenAI API key
- Internet connection for API calls

### Dependencies
```bash
# Core requirements
requests==2.31.0          # HTTP requests
websockets==12.0          # WebSocket communication
python-dotenv==1.0.0      # Environment variable management
openai==1.12.0            # OpenAI API integration
glob2==0.7                # File pattern matching
pathlib2==2.3.7           # Path utilities
```

### Installation Steps
```bash
# 1. Clone repository
git clone <repository-url>
cd AgenticAI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create environment file
cp .env.example .env

# 4. Configure environment variables
# Edit .env with your API keys

# 5. Validate installation
python test_suite.py
```

## 🚀 Usage & Execution

### Basic Execution
```bash
# Run the main application
python main.py

# Alternative runner
python run.py

# Test suite validation
python test_suite.py
```

### Execution Modes
1. **Full Test Run**: Complete audio conversation testing
2. **Validation Mode**: Import and configuration testing
3. **Debug Mode**: Detailed logging and error tracking

### Command Line Options
Currently, the system uses environment variables for configuration. Future versions may include command-line argument support.

## 📊 Data Flow & Processing
## ♻️ Refactors & Improvements

- Consolidated duplicate Streamlit TTS generation logic into `src/services/tts_utils.py`:
  - `list_speakers(engine, language)` returns available speakers per engine.
  - `synthesize_steps(engine, texts, output_dir, ...)` unifies step audio generation across Google/Melo/Coqui.
- Fixed duration calculation in `src/app.py` by tracking `run_start_ms` and computing actual elapsed milliseconds for evaluation summaries.
- Minor resilience improvements around TTS initialization and speaker listing.


### Conversation Data Processing
```
API Response → process_conversation_data() → Structured Data
     ↓
Raw Entries → Audio Segments + Transcript → Step Audio Mapping
     ↓
User Audio + Bot Responses → Conversation History → LLM Evaluation
```

### Audio Processing Pipeline
```
Audio URLs → Download Service → Local Storage → WebSocket Transmission
     ↓
Bot Responses → Conversation Logging → Transcript Extraction → Evaluation
```

### Test Result Generation
```
LLM Evaluation → Result Processing → JSON Storage → File Management
     ↓
Metadata Collection → Summary Generation → Report Creation
```