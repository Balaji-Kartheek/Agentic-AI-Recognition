"""
Audio Service - Handles audio file processing and WebSocket communication
"""
import asyncio
import json
from typing import Dict, List, Any
import os
from src.utils.logger import Logger
from src.utils.conversation import ConversationHistory
from src.models.types import DEFAULTS, MESSAGE_TYPES
from .websocket_service import WebSocketService

class AudioService:
    """Service for handling audio processing and sending"""
    
    @staticmethod
    async def send_audio_file_and_wait_for_response(
        websocket, 
        file_path: str, 
        utterance: str, 
        timeout: int = DEFAULTS.RESPONSE_TIMEOUT, 
        conversation_history: ConversationHistory = None
    ) -> Dict:
        """Send audio file and wait for bot response"""
        try:
            # Check if WebSocket is open
            if websocket.closed:
                return {
                    'success': False,
                    'error': 'WebSocket is not open',
                    'timestamp': Logger._timestamp()
                }
            
            # Read audio file
            try:
                with open(file_path, 'rb') as f:
                    audio_buffer = f.read()
            except Exception as error:
                Logger.error(f"❌ Error reading audio file {file_path}: {error}")
                return {
                    'success': False,
                    'error': str(error),
                    'timestamp': Logger._timestamp()
                }
            
            # Log the User utterance being sent
            print("="*50)
            print(f'🔍 User: {utterance}')
            
            # Log to conversation history if available
            if conversation_history:
                conversation_history.log('User', utterance)
            
            try:
                # Optional: Log audio duration for diagnostics (no modification)
                try:
                    from pydub import AudioSegment as _AS
                    audio_seg = _AS.from_file(file_path)
                    duration_sec = round(len(audio_seg) / 1000.0, 3)
                    channels = getattr(audio_seg, 'channels', '?')
                    frame_rate = getattr(audio_seg, 'frame_rate', '?')
                    # Logger.debug(f"🎚️ Audio info: {os.path.basename(file_path)} | duration={duration_sec}s, channels={channels}, rate={frame_rate}Hz")
                    if duration_sec < 1.0:
                        Logger.warning(f"⚠️ Audio very short (<1s): {os.path.basename(file_path)} may be ignored by ASR")
                except Exception:
                    pass

                # Send audio as binary data
                await websocket.send(audio_buffer)
                # Extra debug: confirm bytes sent
                # Logger.debug(f"📤 Sent audio bytes: {len(audio_buffer)} from {os.path.basename(file_path)}")
                
                # Wait for bot response
                bot_response = await WebSocketService.wait_for_bot_response(websocket, timeout)
                
                # Print Agent response to console
                if bot_response is not None:
                    if isinstance(bot_response, dict):
                        response_text = bot_response.get('response') or bot_response.get('delta')
                        if response_text:
                            print(f'🔍 Agent: {response_text}')
                    elif isinstance(bot_response, str) and bot_response.strip():
                        print(f'🔍 Agent: {bot_response}')
                
                # Log Agent response to conversation history
                if conversation_history and bot_response:
                    if isinstance(bot_response, dict) and bot_response.get('response'):
                        conversation_history.log('Agent', bot_response['response'])
                    elif isinstance(bot_response, str) and bot_response.strip():
                        conversation_history.log('Agent', bot_response)
                
                return {
                    'success': True,
                    'filePath': file_path,
                    'utterance': utterance,
                    'size': len(audio_buffer),
                    'botResponse': bot_response,
                    'timestamp': Logger._timestamp()
                }
                
            except Exception as send_error:
                Logger.error(f"❌ Error sending audio for {file_path}: {send_error}")
                return {
                    'success': False,
                    'error': str(send_error),
                    'timestamp': Logger._timestamp()
                }
                
        except Exception as error:
            return {
                'success': False,
                'error': str(error),
                'timestamp': Logger._timestamp()
            }
    
    @staticmethod
    async def wait_for_target_bot_greeting(websocket, timeout: int = DEFAULTS.RESPONSE_TIMEOUT, conversation_history: ConversationHistory = None) -> Dict:
        """Wait for Agent's initial greeting/message"""
        Logger.info("⏳ Waiting for Agent initial greeting...")
        
        try:
            initial_response = await WebSocketService.wait_for_bot_response(websocket, timeout)

            # Normalize/guard types: initial_response may be dict, str, or bytes
            if isinstance(initial_response, bytes):
                # Ignore binary frames for greeting purposes
                initial_response = {'type': MESSAGE_TYPES.RAW, 'data': '<binary>'}

            if isinstance(initial_response, dict) and initial_response.get('type') != 'no_response':
                # If the first message we get is a session closure, surface as an error to the caller
                if initial_response.get('type') in {MESSAGE_TYPES.SESSION_CLOSE, MESSAGE_TYPES.IDLE_TERMINATE}:
                    return {
                        'success': False,
                        'error': f"Session closed by server: {initial_response.get('type')}",
                        'timestamp': Logger._timestamp()
                    }
                # Print the initial greeting to console if available
                if initial_response.get('response'):
                    print(f"🔍 Agent: {initial_response['response']}")
                    if conversation_history:
                        conversation_history.log('Agent', initial_response['response'])
                elif isinstance(initial_response, str) and initial_response.strip():
                    print(f"🔍 Agent: {initial_response}")
                    if conversation_history:
                        conversation_history.log('Agent', initial_response)
                
                Logger.info("✅ Received Agent greeting, starting conversation...")
                return {
                    'success': True,
                    'greeting': initial_response,
                    'timestamp': Logger._timestamp()
                }
            else:
                return {
                    'success': False,
                    'error': 'No initial greeting received from Agent',
                    'timestamp': Logger._timestamp()
                }
                
        except Exception as error:
            Logger.error("❌ Error waiting for Agent greeting:", str(error))
            return {
                'success': False,
                'error': str(error),
                'timestamp': Logger._timestamp()
            }
    
    @staticmethod
    async def send_all_audio_files_sequentially(
        websocket,
        download_results: List[Dict],
        step_audio: Dict,
        conversation_id: str,
        conversation_history: ConversationHistory = None
    ) -> List[Dict]:
        """Send all audio files sequentially, waiting for bot response after each"""
        audio_results = []
        
        # Initialize or reuse conversation history logging
        if conversation_history is None:
            conversation_history = ConversationHistory(conversation_id)
            print(f"📝 Conversation history will be saved to: logs/{conversation_history.filename}")
        else:
            # If already provided, still show the file path once here for clarity
            print(f"📝 Conversation history will be saved to: logs/{conversation_history.filename}")
        
        # The caller is responsible for waiting for greeting (if needed)
        
        # Now send audio steps as responses to the Agent
        Logger.info(f"🎧 Preparing to send {len(download_results)} audio files...")
        for i, download_result in enumerate(download_results):
            if download_result['success']:
                try:
                    # Ensure websocket is still open before sending next file
                    if getattr(websocket, 'closed', False):
                        Logger.error("❌ WebSocket is closed before sending next audio. Aborting sequence.")
                        audio_results.append({
                            'step': download_result['step'],
                            'stepNumber': i + 1,
                            'success': False,
                            'error': 'WebSocket closed before send'
                        })
                        break

                    file_path = download_result['filePath']
                    if not os.path.exists(file_path):
                        Logger.error(f"❌ Audio file missing on disk: {file_path}")
                        audio_results.append({
                            'step': download_result['step'],
                            'stepNumber': i + 1,
                            'success': False,
                            'error': 'File not found'
                        })
                        continue

                    send_result = await AudioService.send_audio_file_and_wait_for_response(
                        websocket,
                        file_path,
                        step_audio[download_result['step']]['utterance'],
                        DEFAULTS.RESPONSE_TIMEOUT,
                        conversation_history
                    )
                    
                    audio_results.append({
                        'step': download_result['step'],
                        'stepNumber': i + 1,
                        **send_result
                    })
                    
                    # Add a small delay between steps (optional)
                    if i < len(download_results) - 1:
                        await asyncio.sleep(DEFAULTS.STEP_DELAY / 1000)
                        
                except Exception as error:
                    Logger.error(f"❌ Failed to send {download_result['step']}: {error}")
                    audio_results.append({
                        'step': download_result['step'],
                        'stepNumber': i + 1,
                        'success': False,
                        'error': str(error)
                    })
            else:
                audio_results.append({
                    'step': download_result['step'],
                    'stepNumber': i + 1,
                    'success': False,
                    'error': 'Download failed',
                    'downloadError': download_result.get('error')
                })
        
        return audio_results 

    @staticmethod
    async def send_text_and_wait_for_response(
        websocket,
        text: str,
        timeout: int = DEFAULTS.RESPONSE_TIMEOUT,
        conversation_history: ConversationHistory = None
    ) -> Dict:
        """Send a text message and wait for bot response"""
        try:
            if getattr(websocket, 'closed', False):
                return {
                    'success': False,
                    'error': 'WebSocket is not open',
                    'timestamp': Logger._timestamp()
                }

            # Log outgoing text (User utterance)
            print(f'🔍 User: {text}')
            if conversation_history:
                conversation_history.log('User', text)

            # Send text
            await WebSocketService.send_text_message(websocket, text)

            # Wait for bot response
            bot_response = await WebSocketService.wait_for_bot_response(websocket, timeout)

            # Print and log bot response
            if bot_response is not None:
                if isinstance(bot_response, dict):
                    response_text = bot_response.get('response') or bot_response.get('delta')
                    if response_text:
                        print(f'🔍 Agent: {response_text}')
                        if conversation_history:
                            conversation_history.log('Agent', response_text)
                elif isinstance(bot_response, str) and bot_response.strip():
                    print(f'🔍 Agent: {bot_response}')
                    if conversation_history:
                        conversation_history.log('Agent', bot_response)

            return {
                'success': True,
                'utterance': text,
                'botResponse': bot_response,
                'timestamp': Logger._timestamp()
            }
        except Exception as error:
            Logger.error("❌ Error sending text:", str(error))
            return {
                'success': False,
                'error': str(error),
                'timestamp': Logger._timestamp()
            }

    @staticmethod
    async def send_all_text_steps_sequentially(
        websocket,
        texts: List[str],
        conversation_id: str,
        conversation_history: ConversationHistory = None
    ) -> List[Dict]:
        """Send all text steps sequentially, waiting for bot response after each"""
        text_results: List[Dict] = []

        # Initialize or reuse conversation history logging
        if conversation_history is None:
            conversation_history = ConversationHistory(conversation_id)
            print(f"📝 Conversation history will be saved to: logs/{conversation_history.filename}")
        else:
            print(f"📝 Conversation history will be saved to: logs/{conversation_history.filename}")

        Logger.info(f"💬 Preparing to send {len(texts)} text step(s)...")
        for i, text in enumerate(texts):
            if getattr(websocket, 'closed', False):
                Logger.error("❌ WebSocket is closed before sending next text. Aborting sequence.")
                text_results.append({
                    'stepNumber': i + 1,
                    'success': False,
                    'error': 'WebSocket closed before send'
                })
                break

            send_result = await AudioService.send_text_and_wait_for_response(
                websocket,
                text,
                DEFAULTS.RESPONSE_TIMEOUT,
                conversation_history
            )
            text_results.append({
                'step': f'step_{i+1}',
                'stepNumber': i + 1,
                **send_result
            })

            # Small delay between steps
            if i < len(texts) - 1:
                await asyncio.sleep(DEFAULTS.STEP_DELAY / 1000)

        return text_results