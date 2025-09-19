# Handling Dynamic Conversations in the AgenticAI Suite

## Current Implementation

The current conversation flow is mostly linear and follows a predefined script. Here's a summary of how it works:

1.  **`AudioService.send_all_audio_files_sequentially`**: This is the main function that orchestrates the conversation. It iterates through a list of audio files and sends them one by one to the bot.
2.  **`WebSocketService`**: This service is responsible for the low-level communication with the bot. It sends the audio files and receives the bot's responses.
3.  **`OpenAIService.evaluate_conversation`**: After the conversation is finished, this service is used to evaluate the conversation against a "golden" transcript.

The main limitation of this approach is that it's not very flexible. The conversation is tightly coupled to the predefined script, and it's difficult to handle unexpected user inputs or deviations from the script.

## Achieving a More Dynamic Conversation Flow

To handle dynamic conversations, you need to introduce a mechanism that can make decisions based on the bot's responses. This will allow the conversation to adapt to different situations and user inputs.

Here are a few ways you can achieve this:

### 1. State Machine

A state machine is a great way to model a conversation. Each state represents a point in the conversation, and the transitions between states are triggered by the bot's responses.

Here's an example of how you could implement a state machine for your conversation:

```python
class ConversationState:
    GREETING = "GREETING"
    APPOINTMENT_CONFIRMATION = "APPOINTMENT_CONFIRMATION"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    LAST_NAME = "LAST_NAME"
    ZIP_CODE = "ZIP_CODE"
    END = "END"

class ConversationManager:
    def __init__(self):
        self.state = ConversationState.GREETING

    def handle_response(self, response):
        if self.state == ConversationState.GREETING:
            # Transition to the next state based on the response
            if "confirm your appointment" in response:
                self.state = ConversationState.APPOINTMENT_CONFIRMATION
                # Send the next audio file
        elif self.state == ConversationState.APPOINTMENT_CONFIRMATION:
            if "verify your identity" in response:
                self.state = ConversationState.IDENTITY_VERIFICATION
                # ...
```

You would need to integrate this state machine into your `AudioService` to guide the conversation.

### 2. Intent Recognition

You can use a natural language understanding (NLU) service to recognize the intent of the bot's responses. This will allow you to understand what the bot is trying to do and respond accordingly.

There are many NLU services available, both cloud-based (like Google Dialogflow, Amazon Lex, or Microsoft LUIS) and open-source (like Rasa).

Here's how you could use an NLU service in your `AudioService`:

```python
class AudioService:
    def __init__(self, websocket_service, nlu_service):
        self.websocket_service = websocket_service
        self.nlu_service = nlu_service

    async def handle_conversation(self):
        # ...
        response = await self.websocket_service.receive()
        intent = self.nlu_service.recognize_intent(response)

        if intent == "request_date_of_birth":
            # Send the date of birth audio file
        elif intent == "request_last_name":
            # Send the last name audio file
        # ...
```

### 3. Combination of State Machine and Intent Recognition

You can combine a state machine with intent recognition to create a powerful and flexible conversation manager. The state machine can be used to model the overall conversation flow, while intent recognition can be used to handle the details of each state.

For example, in the `IDENTITY_VERIFICATION` state, you could use intent recognition to determine which piece of information the bot is asking for (date of birth, last name, or zip code).

### Implementation in `src/services/adaptive_flow_service.py`

The project already has a service that seems to be designed for this purpose: `src/services/adaptive_flow_service.py`. This service is currently used to detect if the bot is asking for confirmation, but it could be extended to handle more complex conversation logic.

Here's how you could modify the `AdaptiveFlowService` to implement a state machine:

```python
# src/services/adaptive_flow_service.py
import re

class ConversationState:
    # ... (as defined above)

class AdaptiveFlowService:
    CONFIRMATION_PATTERNS = [
        "Just to confirm",
        "did you mean",
        "let's verify"
    ]

    def __init__(self):
        self.state = ConversationState.GREETING

    def get_next_action(self, last_bot_text):
        if self.state == ConversationState.GREETING:
            if "confirm your appointment" in last_bot_text:
                self.state = ConversationState.APPOINTMENT_CONFIRMATION
                return {'action': 'send_next_step', 'reason': 'Bot is asking to confirm appointment'}
        elif self.state == ConversationState.APPOINTMENT_CONFIRMATION:
            if "verify your identity" in last_bot_text:
                self.state = ConversationState.IDENTITY_VERIFICATION
                return {'action': 'send_next_step', 'reason': 'Bot is asking to verify identity'}
        # ...

        if self._matches_any(last_bot_text, self.CONFIRMATION_PATTERNS):
            return { 'action': 'repeat_previous', 'reason': 'Bot asked for confirmation/clarification' }

        return { 'action': 'send_next_step', 'reason': 'Default action' }

    @staticmethod
    def _matches_any(text: str, patterns: list[str]) -> bool:
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
```

You would then need to modify `AudioService` to use this service to decide the next action.

```python
# src/services/audio_service.py

class AudioService:
    def __init__(self, websocket_service, adaptive_flow_service):
        self.websocket_service = websocket_service
        self.adaptive_flow_service = adaptive_flow_service

    async def send_all_audio_files_sequentially(self, audio_files):
        # ...
        current_step = 0
        while current_step < len(audio_files):
            # ...
            response = await self.websocket_service.receive()
            action = self.adaptive_flow_service.get_next_action(response)

            if action['action'] == 'repeat_previous':
                # Send the previous audio file again
                pass
            elif action['action'] == 'send_next_step':
                # Send the next audio file
                current_step += 1
            # ...
```

This is a high-level overview of how you can handle dynamic conversations in your project. The best approach for you will depend on the specific requirements of your project.

I would recommend starting with a simple state machine and then gradually adding more complex logic as needed. Using an NLU service can be very powerful, but it also adds more complexity to your project.
