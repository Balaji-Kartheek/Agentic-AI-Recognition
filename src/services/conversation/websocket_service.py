"""
WebSocket Service - Handles WebSocket connections and messaging (conversation namespace)
"""
import asyncio
import json
import time
import websockets
from config.config import config
from typing import Dict
from src.utils.logger import Logger
from src.models.types import MESSAGE_TYPES, DEFAULTS


class WebSocketService:
    """Service for managing WebSocket connections"""

    @staticmethod
    async def create_connection(session_data: Dict) -> Dict:
        """Create WebSocket connection for audio/text streaming"""
        try:
            # The session_data should contain the API response with a 'token' field
            token = session_data.get('token')
            if not token:
                # Try to extract from nested data structure if it exists
                if 'data' in session_data and isinstance(session_data['data'], dict):
                    token = session_data['data'].get('token')

                if not token:
                    Logger.error("❌ Token not found in session data")
                    Logger.error(f"Session data structure: {session_data}")
                    raise ValueError("Token not found in session data")

            # Construct WebSocket URL with token and mode
            ws_url = f"{config.ws_url}?jst={token}&mode={config.conversation_mode}"

            Logger.info(f"🔌 Connecting to WebSocket")

            # Create WebSocket connection
            websocket = await websockets.connect(ws_url)

            Logger.success("✅ WebSocket connection established")

            # Send greeting after connection (following bot's pattern)
            await asyncio.sleep(1)
            if websocket.open:
                await websocket.send(json.dumps({
                    'type': MESSAGE_TYPES.SESSION_GREETING
                }))

            return {
                'success': True,
                'websocket': websocket,
                'url': ws_url,
                'timestamp': Logger._timestamp()
            }

        except Exception as error:
            Logger.error("❌ Failed to create WebSocket connection:", str(error))
            return {
                'success': False,
                'error': str(error),
                'timestamp': Logger._timestamp()
            }

    @staticmethod
    async def handle_message(websocket, data):
        """Handles incoming WebSocket messages"""
        try:
            # Check if it's a binary message (audio data)
            if isinstance(data, bytes):
                return {
                    'type': MESSAGE_TYPES.AUDIO_DATA,
                    'data': data
                }
            else:
                # Parse JSON message
                message = json.loads(data)

                if message.get('type') in [
                    MESSAGE_TYPES.RESPONSE_TEXT,
                    MESSAGE_TYPES.RESPONSE_TEXT_DELTA,
                    MESSAGE_TYPES.AUDIO_KILL,
                    MESSAGE_TYPES.SKILL_TRANSFER,
                    MESSAGE_TYPES.IDLE_WARNING,
                    MESSAGE_TYPES.IDLE_TERMINATE,
                    MESSAGE_TYPES.SESSION_OPEN,
                    MESSAGE_TYPES.SESSION_CLOSE
                ]:
                    if message.get('type') == MESSAGE_TYPES.RESPONSE_TEXT:
                        print('🔍 Agent: ', message.get('response', ''))
                    else:
                        print("Unable to get the response")
                    return message
                else:
                    return message

        except json.JSONDecodeError:
            return {
                'type': MESSAGE_TYPES.RAW,
                'data': data
            }
        except Exception as parse_error:
            Logger.error("❌ Error parsing message:", str(parse_error))
            return None

    @staticmethod
    async def wait_for_bot_response(websocket, timeout: int = None) -> Dict:
        """Wait for bot response with timeout"""
        if timeout is None:
            timeout = DEFAULTS.RESPONSE_TIMEOUT

        try:
            # Convert timeout to seconds
            timeout_seconds = timeout / 1000

            responses = []
            last_message_time = asyncio.get_event_loop().time() if hasattr(asyncio.get_event_loop(), 'time') else time.time()
            inactivity_timeout = DEFAULTS.BOT_RESPONSE_WAIT / 1000
            has_complete_text_response = False

            async def message_handler():
                nonlocal responses, last_message_time, has_complete_text_response

                try:
                    while True:
                        message = await websocket.recv()
                        last_message_time = asyncio.get_event_loop().time() if hasattr(asyncio.get_event_loop(), 'time') else time.time()
                        responses.append(message)

                        # Check if we have a complete text response
                        if isinstance(message, str):
                            try:
                                parsed = json.loads(message)
                                if parsed.get('type') == MESSAGE_TYPES.RESPONSE_TEXT and parsed.get('response'):
                                    has_complete_text_response = True
                                    # Bot has finished - wait a short time for any final messages
                                    await asyncio.sleep(0.5)
                                    return parsed
                            except json.JSONDecodeError:
                                pass

                        await asyncio.sleep(0.1)

                except websockets.exceptions.ConnectionClosed:
                    pass

            # Wait for message with timeout
            try:
                result = await asyncio.wait_for(message_handler(), timeout=timeout_seconds)
                return result
            except asyncio.TimeoutError:
                if responses:
                    best_response = None
                    for response in responses:
                        if isinstance(response, str):
                            try:
                                parsed = json.loads(response)
                                if parsed.get('type') == MESSAGE_TYPES.RESPONSE_TEXT and parsed.get('response'):
                                    best_response = parsed
                                    break
                            except json.JSONDecodeError:
                                continue
                    if not best_response:
                        for response in responses:
                            if isinstance(response, str):
                                try:
                                    parsed = json.loads(response)
                                    if parsed.get('type') == MESSAGE_TYPES.RESPONSE_TEXT_DELTA and parsed.get('delta'):
                                        best_response = parsed
                                        break
                                except json.JSONDecodeError:
                                    continue
                    if not best_response and responses:
                        best_response = responses[0]
                    return best_response or {'type': MESSAGE_TYPES.NO_RESPONSE}

                return {'type': MESSAGE_TYPES.NO_RESPONSE}

        except Exception as error:
            Logger.error("❌ Error waiting for bot response:", str(error))
            return {
                'type': 'error',
                'response': None,
                'error': str(error),
                'timestamp': Logger._timestamp()
            }

    @staticmethod
    async def send_ping(websocket):
        """Sends ping to keep session alive"""
        if websocket.open:
            await websocket.send(json.dumps({
                'type': MESSAGE_TYPES.SESSION_PING
            }))

    @staticmethod
    def start_ping_interval(websocket, interval: int = None):
        """Start ping interval to keep session alive"""
        if interval is None:
            interval = DEFAULTS.PING_INTERVAL

        async def ping_loop():
            while websocket.open:
                try:
                    await asyncio.sleep(interval / 1000)
                    await WebSocketService.send_ping(websocket)
                    Logger.debug("🏓 Ping sent to keep session alive")
                except Exception as error:
                    Logger.error("❌ Ping failed:", str(error))
                    break

        loop = asyncio.get_running_loop()
        task = loop.create_task(ping_loop())

        def stop_ping():
            task.cancel()

        return stop_ping

    @staticmethod
    async def disconnect(websocket, send_disconnect: bool = True):
        """Properly disconnects from WebSocket session"""
        try:
            if websocket.open and send_disconnect:
                await websocket.send(json.dumps({
                    'type': MESSAGE_TYPES.SESSION_DISCONNECT
                }))

            await websocket.close()
            Logger.info("🔌 WebSocket connection closed")
        except Exception as error:
            Logger.error("❌ Error closing WebSocket:", str(error))

    @staticmethod
    async def send_text_message(websocket, text: str) -> Dict:
        """Sends text message to the bot"""
        try:
            if not websocket.open:
                return {
                    'success': False,
                    'error': 'WebSocket is not open',
                    'timestamp': Logger._timestamp()
                }

            await websocket.send(json.dumps({
                'type': MESSAGE_TYPES.TEXT,
                'text': text
            }))

            return {
                'success': True,
                'text': text,
                'timestamp': Logger._timestamp()
            }

        except Exception as error:
            Logger.error("❌ Error sending text:", str(error))
            return {
                'success': False,
                'error': str(error),
                'timestamp': Logger._timestamp()
            }


