# Avaamo Agentic Audio Evaluator - Python Suite

A Python application for evaluating Avaamo conversation transcripts and audio using OpenAI API for intelligent conversation analysis.

## Overview

This application automates the testing of Avaamo conversational AI bots by:

*   **Audio Processing:** Downloads and processes audio files from Avaamo conversations
*   **WebSocket Communication:** Establishes real-time communication with the bot
*   **Transcript Evaluation:** Uses OpenAI API to compare the actual conversation transcript with a "golden" transcript to evaluate the bot's accuracy.
*   **Automated Testing:** Streamlines the QA process for conversational AI systems

## ✨ Features

*   **Automated Conversation Simulation:** Fetches a predefined conversation from the Avaamo platform and simulates it by sending audio files through a WebSocket connection.
*   **Audio Handling:** Downloads the necessary audio files for each step of the conversation.
*   **Transcript Evaluation:** Uses OpenAI API to compare the actual conversation transcript with a "golden" transcript to evaluate the bot's accuracy.
*   **Detailed Test Reports:** Generates a summary of the test results, including a pass/fail status and a detailed breakdown of the evaluation.
*   **Environment-based Configuration:** Uses a `.env` file to manage sensitive information like API keys, making the application secure and easy to configure.

## 🚀 Quick Start

### Prerequisites

*   Python 3.8 or higher
*   Avaamo API access token
*   OpenAI API key

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd python-suite
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create environment file:**
    ```bash
    cp .env.example .env
    # Edit .env with your API keys
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Avaamo Configuration
AGENT_ACCESS_TOKEN=your_avaamo_access_token_here

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o
```

*   `AGENT_ACCESS_TOKEN`: Your Avaamo API access token.
*   `OPENAI_API_KEY`: Your OpenAI API key used for evaluation.
*   `LLM_MODEL`: The LLM model name. Defaults to OpenAI's GPT-4o model.

## 🏗️ Project Structure

```
python-suite/
├── config/
│   └── config.py              # Configuration management
├── src/
│   ├── models/
│   │   └── types.py           # Type definitions and constants
│   ├── services/
│   │   ├── session_service.py      # Session management
│   │   ├── websocket_service.py    # WebSocket communication
│   │   ├── download_service.py     # Audio file downloads
│   │   ├── audio_service.py        # Audio processing
│   │   ├── openai_service.py       # OpenAI API integration
│   │   └── test_results_service.py # Test result management
│   ├── utils/
│   │   ├── logger.py               # Logging utilities
│   │   └── conversation.py         # Conversation processing
│   └── app.py                      # Main application logic
├── logs/                           # Conversation logs
├── test_results/                   # Test evaluation results
├── downloads/                      # Downloaded audio files
├── requirements.txt                # Python dependencies
├── main.py                         # Application entry point
└── README.md                       # This file
```

## 🔄 How It Works

1.  **Create Session:** The application creates a WebSocket session with the Avaamo platform.
2.  **Fetch Conversation:** It retrieves the conversation data, including the transcript and audio file URLs.
3.  **Download Audio:** It downloads all the audio files associated with the conversation steps.
4.  **Establish WebSocket Connection:** It establishes a WebSocket connection to the Avaamo platform.
5.  **Simulate Conversation:** It sends the downloaded audio files sequentially through the WebSocket, simulating a user talking to the bot.
6.  **Evaluate Transcript:** Once the conversation is complete, it uses OpenAI API to compare the actual transcript (what the bot understood) with the "golden" transcript (the expected conversation).
7.  **Generate Report:** It generates a test report with the evaluation results and saves it to the `logs` directory.

## 📚 Dependencies

*   [requests](https://pypi.org/project/requests/) - HTTP library for API calls
*   [websockets](https://pypi.org/project/websockets/) - WebSocket client library
*   [python-dotenv](https://pypi.org/project/python-dotenv/) - Environment variable management
*   [openai](https://pypi.org/project/openai/) - OpenAI API client
*   [pathlib2](https://pypi.org/project/pathlib2/) - Path manipulation utilities

## 🧪 Testing

The application includes comprehensive testing capabilities:

*   **Automated Test Execution:** Runs through the entire conversation flow automatically
*   **Result Validation:** Uses OpenAI to evaluate conversation quality
*   **Detailed Reporting:** Generates comprehensive test reports
*   **Historical Tracking:** Maintains logs of all test runs

## 🚨 Troubleshooting

### Common Issues

1.  **WebSocket Connection Failed:** Check your Avaamo API credentials and network connectivity
2.  **Audio Download Failed:** Verify the audio URLs are accessible and the files exist
3.  **LLM Evaluation Failed:** Ensure your OpenAI API key is valid and has sufficient credits
4.  **Configuration Errors:** Verify all required environment variables are set

### Debug Mode

Enable debug logging by setting the `DEBUG` environment variable:

```env
DEBUG=true
```

## 🤝 Contributing

1.  Fork the repository
2.  Create a feature branch
3.  Make your changes
4.  Add tests if applicable
5.  Submit a pull request

## 📄 License

This project is licensed under the ISC License.

## 🆘 Support

For support and questions:

*   Check the troubleshooting section above
*   Review the logs in the `logs/` directory
*   Check test results in the `test_results/` directory
*   Open an issue on the repository 