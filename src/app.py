"""
Main Application - Orchestrates the Avaamo Audio Evaluator workflow
"""
import asyncio
import glob
import os
import time
from pathlib import Path
from typing import Dict, Any

# Disable tokenizers parallelism to avoid fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from src.utils.logger import Logger
from src.models.types import PATHS, DEFAULTS

# Import all the services
from src.services.conversation.session_service import SessionService
from src.services.conversation.websocket_service import WebSocketService
from src.services.io.download_service import DownloadService
from src.services.conversation.audio_service import AudioService
from src.services.evaluation.openai_service import OpenAIService
from src.services.io.test_results_service import TestResultsService
from src.services.tts.google_tts_service import GoogleTTSService
from src.services.conversation.dynamic_run_service import DynamicRunService


class AvaamoAudioEvaluator:
    """Main application class for Avaamo Audio Evaluator"""
    
    def __init__(self, config):
        self.config = config
    
    async def run(self) -> Dict[str, Any]:
        """Main execution function - processes all conversation IDs"""
        Logger.header('🚀🚀🚀🚀 Avaamo Agentic Audio Evaluator - Multi-Conversation Mode')
        
        # Validate configuration
        if not self._validate_config():
            return {'success': False, 'error': 'Configuration validation failed'}
        
        # Check if we have multiple conversation IDs
        if hasattr(self.config, 'conversation_ids') and len(self.config.conversation_ids) > 1:
            Logger.info(f"📋 Processing {len(self.config.conversation_ids)} conversations")
            return await self._run_multiple_conversations()
        else:
            Logger.info("📋 Processing single conversation")
            return await self._run_single_conversation(self.config.conversation_id)
    
    async def _run_multiple_conversations(self) -> Dict[str, Any]:
        """Run the evaluation for multiple conversation IDs"""
        all_results = []
        total_conversations = len(self.config.conversation_ids)
        
        for index, conversation_id in enumerate(self.config.conversation_ids, 1):
            Logger.header(f"🔄 Processing Conversation {index}/{total_conversations}: {conversation_id}")
            
            try:
                result = await self._run_single_conversation(conversation_id)
                all_results.append({
                    'conversation_id': conversation_id,
                    'success': result.get('success', False),
                    'result': result
                })
                
                if result.get('success'):
                    Logger.success(f"✅ Conversation {index}/{total_conversations} completed successfully")
                else:
                    Logger.error(f"❌ Conversation {index}/{total_conversations} failed: {result.get('error', 'Unknown error')}")
                
                # Add a small delay between conversations
                if index < total_conversations:
                    Logger.info("⏳ Waiting 2 seconds before next conversation...")
                    await asyncio.sleep(2)
                    
            except Exception as error:
                Logger.error(f"💥 Error processing conversation {conversation_id}: {error}")
                all_results.append({
                    'conversation_id': conversation_id,
                    'success': False,
                    'error': str(error)
                })
        
        # Summary
        successful = len([r for r in all_results if r['success']])
        failed = len([r for r in all_results if not r['success']])
        
        Logger.header("📊 Multi-Conversation Summary")
        Logger.info(f"✅ Successful: {successful}/{total_conversations}")
        Logger.info(f"❌ Failed: {failed}/{total_conversations}")
        
        return {
            'success': successful > 0,
            'total_conversations': total_conversations,
            'successful': successful,
            'failed': failed,
            'results': all_results
        }
    
    async def _run_single_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Run the evaluation for a single conversation ID"""
        # Temporarily set the conversation ID
        original_conversation_id = self.config.conversation_id
        self.config.conversation_id = conversation_id
        run_start_ms = int(time.time() * 1000)
        
        try:
            # Step 1: Create WebSocket session
            Logger.step(1, 'Creating session...')
            session_result = await SessionService.create_session(self.config)
            
            if not session_result['success']:
                Logger.error('\n💥 Failed to create session')
                return {'success': False, 'error': 'Session creation failed'}
            
            # Step 2: Prepare inputs depending on mode
            if getattr(self.config, 'synthetic_mode', False):
                # If conversation_mode is text, bypass audio entirely
                from config.config import config as runtime_cfg
                if getattr(runtime_cfg, 'conversation_mode', 'voice') == 'text' and (self.config.synthetic_files is None or len(self.config.synthetic_files) == 0):
                    Logger.step(2, 'Preparing synthetic text steps...')
                    provided_texts = list(self.config.synthetic_texts or [])
                    if not provided_texts:
                        return {'success': False, 'error': 'No synthetic text steps provided'}
                    conversation_identifier = 'synthetic'
                    result = {
                        'success': True,
                        'conversation_id': conversation_identifier,
                        'data': {
                            'step_audio': {},
                            'transcript': 'Synthetic text run (no audio)'
                        }
                    }
                    download_results = []
                    Logger.success(f"\n✅ Prepared {len(provided_texts)} text step(s)")
                else:
                    Logger.step(2, 'Preparing synthetic audio files...')
                    # Build pseudo download_results and step_audio from provided synthetic files/texts
                    provided_files = list(self.config.synthetic_files or [])
                    provided_texts = list(self.config.synthetic_texts or [])
                    if not provided_files:
                        return {'success': False, 'error': 'No synthetic files provided'}

                    # Align texts length to files
                    if len(provided_texts) < len(provided_files):
                        provided_texts = (provided_texts + [""] * len(provided_files))[:len(provided_files)]

                    # Construct structures compatible with AudioService
                    conversation_identifier = 'synthetic'
                    step_audio_map = {}
                    download_results = []
                    for index, file_path in enumerate(provided_files, start=1):
                        step_key = f"step_{index}"
                        step_audio_map[step_key] = { 'utterance': provided_texts[index - 1] }
                        download_results.append({
                            'success': True,
                            'step': step_key,
                            'filePath': str(file_path)
                        })
                    # Create a "result"-like object for downstream fields
                    result = {
                        'success': True,
                        'conversation_id': conversation_identifier,
                        'data': {
                            'step_audio': step_audio_map,
                            'transcript': 'Synthetic run (no golden transcript)'
                        }
                    }
                    Logger.success(f"\n✅ Prepared {len(download_results)} synthetic file(s)")
            elif getattr(self.config, 'dynamic_synthetic_mode', False):
                Logger.step(2, 'Preparing for dynamic real-time conversation...')
                
                if not self.config.openai_api_key:
                    return {'success': False, 'error': 'OpenAI API key required for dynamic synthetic mode'}
                
                # For dynamic mode, we'll generate steps in real-time during conversation
                # Create minimal structures to satisfy the flow
                conversation_identifier = 'dynamic_synthetic'
                result = {
                    'success': True,
                    'conversation_id': conversation_identifier,
                    'data': {
                        'step_audio': {},  # Will be populated during conversation
                        'transcript': f'Dynamic synthetic run: {getattr(self.config, "dynamic_scenario", "Unknown scenario")}'
                    }
                }
                download_results = []  # Will be populated during conversation
                Logger.success(f"\n✅ Prepared for dynamic real-time conversation")
            else:
                # Human flow: Fetch conversation and download audio files
                Logger.step(2, 'Fetching conversation data...')
                result = await SessionService.fetch_conversation(self.config)
                
                if not result['success']:
                    Logger.error('\n💥 Failed to fetch conversation data')
                    return {'success': False, 'error': 'Conversation fetch failed'}
                
                Logger.success(f"\n✅ Successfully processed conversation: {result['conversation_id']}")
                
                # Step 3: Clear existing files and download all step audio files
                Logger.step(3, 'Clearing existing files and downloading audio files...')
                download_results = await DownloadService.download_all_step_audio(
                    result['data']['step_audio'], 
                    self.config
                )
            
            # Check if all downloads were successful
            failed_downloads = [r for r in download_results if not r['success']]
            if failed_downloads:
                Logger.error(f'\n⚠️ Some audio files failed to download: {len(failed_downloads)}')
                Logger.error('Proceeding with successful downloads only...')
            
            # Next step: Create WebSocket connection (after inputs are ready)
            next_step_index = 3 if not getattr(self.config, 'synthetic_mode', False) else 3
            Logger.step(next_step_index, 'Creating WebSocket connection...')
            ws_result = await WebSocketService.create_connection(session_result['data'])
            
            if not ws_result['success']:
                Logger.error('\n💥 Failed to create WebSocket connection')
                return {'success': False, 'error': 'WebSocket connection failed'}
            
            Logger.success('\n✅ WebSocket connection established successfully')
            
            # Start ping interval to keep session alive
            stop_ping_interval = WebSocketService.start_ping_interval(ws_result['websocket'], 30000)
            
            # Create conversation history before greeting so the greeting is logged
            from src.utils.conversation import ConversationHistory
            conversation_history = ConversationHistory(result['conversation_id'])
            # Announce log file path
            Logger.info(f"📝 Conversation history will be saved to: logs/{conversation_history.filename}")
            # Wait for Agent initial greeting before sending any audio, and log it
            greeting_result = await AudioService.wait_for_target_bot_greeting(ws_result['websocket'], conversation_history=conversation_history)
            if not greeting_result.get('success'):
                stop_ping_interval()
                await WebSocketService.disconnect(ws_result['websocket'], True)
                return {'success': False, 'error': greeting_result.get('error', 'No greeting from bot')}

            # Send messages through WebSocket
            if getattr(self.config, 'dynamic_synthetic_mode', False):
                Logger.step(next_step_index + 1, 'Starting dynamic real-time conversation...')
                audio_results = await DynamicRunService.run_dynamic_conversation(
                    websocket=ws_result['websocket'],
                    conversation_history=conversation_history,
                    scenario=getattr(self.config, 'dynamic_scenario', 'Confirm the appointment'),
                    max_steps=int(getattr(self.config, 'dynamic_max_steps', 6)),
                    openai_api_key=self.config.openai_api_key,
                    llm_model=self.config.llm_model,
                    temperature=float(getattr(self.config, 'dynamic_temperature', 0.3))
                )
            else:
                from config.config import config as runtime_cfg
                if getattr(runtime_cfg, 'conversation_mode', 'voice') == 'text' and getattr(self.config, 'synthetic_mode', False) and (self.config.synthetic_files is None or len(self.config.synthetic_files) == 0):
                    Logger.step(next_step_index + 1, 'Sending text steps...')
                    provided_texts = list(self.config.synthetic_texts or [])
                    audio_results = await AudioService.send_all_text_steps_sequentially(
                        ws_result['websocket'],
                        provided_texts,
                        result['conversation_id'],
                        conversation_history
                    )
                else:
                    Logger.step(next_step_index + 1, 'Sending audio files...')
                    audio_results = await AudioService.send_all_audio_files_sequentially(
                        ws_result['websocket'], 
                        download_results, 
                        result['data']['step_audio'],
                        result['conversation_id'],
                        conversation_history
                    )
            
            # Stop ping interval and properly disconnect
            stop_ping_interval()
            await WebSocketService.disconnect(ws_result['websocket'], True)
            
            Logger.success('\n✅ Audio sending completed successfully!')
            
            # Step 6: Evaluate conversation using LLM (if API key is provided)
            if self.config.openai_api_key:
                Logger.step(6, 'Evaluating conversation with LLM...')
                
                test_id = TestResultsService.generate_test_id(result['conversation_id'])
                
                # Get the conversation history file path
                conversation_history_pattern = f"logs/conversation_history_{result['conversation_id']}_*.txt"
                history_files = glob.glob(conversation_history_pattern)
                
                if history_files:
                    latest_history_file = max(history_files, key=Path)  # Get the most recent
                    conversation_history_content = TestResultsService.read_conversation_history(latest_history_file)
                    
                    if conversation_history_content:
                        # Extract clean transcript
                        actual_transcript = TestResultsService.extract_clean_transcript(conversation_history_content)
                        
                        # Initialize LLM service
                        openai_service = OpenAIService({
                            'api_key': self.config.openai_api_key,
                            'model': self.config.llm_model
                        })
                        
                        # Evaluate the conversation
                        evaluation_result = await openai_service.evaluate_conversation(
                            actual_transcript,
                            result['data'].get('transcript', 'No golden transcript available'),
                            test_id,
                            self.config.channel_id,
                            getattr(self.config, 'run_type', 'human'),
                            getattr(self.config, 'dynamic_scenario', None)
                        )
                        
                        # Save test result
                        if evaluation_result['success']:
                            final_test_result = TestResultsService.create_test_summary(evaluation_result['result'], {
                                'duration': max(0, int((time.time() * 1000) - run_start_ms)),
                                'audioFilesSent': len([r for r in download_results if r['success']]),
                                'totalMessages': len(audio_results),
                                'evaluation_model': self.config.llm_model
                            })
                        else:
                            final_test_result = TestResultsService.create_test_summary(evaluation_result['fallback_result'], {
                                'duration': max(0, int((time.time() * 1000) - run_start_ms)),
                                'audioFilesSent': len([r for r in download_results if r['success']]),
                                'totalMessages': len(audio_results),
                                'evaluation_model': self.config.llm_model
                            })
                        
                        # Save the test result to file
                        save_result = await TestResultsService.save_test_result(final_test_result, result['conversation_id'])
                        
                        if save_result['success']:
                            Logger.info(f"📊 Result: {final_test_result['scenario_result'].upper()}")
                            Logger.info(f"📁 Test result saved to: {save_result['filename']}")
                        else:
                            Logger.error('❌ Failed to save test result')
                        
                    else:
                        Logger.error('❌ Could not read conversation history for evaluation')
                else:
                    Logger.error('❌ No conversation history file found for evaluation')
            else:
                Logger.info('ℹ️ Skipping LLM evaluation (no API key provided)')
            
            Logger.success('\n✅ All steps completed successfully!')
            Logger.info(f"📁 Downloaded files are stored in: {PATHS.AUDIO_STEPS}")
            
            return {
                'success': True,
                'session_result': session_result,
                'conversation_result': result,
                'download_results': download_results,
                'audio_results': audio_results
            }
            
        except Exception as error:
            Logger.error('💥 Application error:', str(error))
            return {'success': False, 'error': str(error)}
        finally:
            # Restore original conversation ID
            self.config.conversation_id = original_conversation_id
    
    def _validate_config(self) -> bool:
        """Validate the configuration"""
        required_fields = ['access_token', 'channel_id', 'base_url']
        
        for field in required_fields:
            if not getattr(self.config, field, None):
                Logger.error(f"❌ Missing required configuration: {field}")
                return False
        
        return True 