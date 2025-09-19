"""
Session Service - Handles session creation and management
"""
import requests
from typing import Dict, Optional
from src.utils.logger import Logger

class SessionService:
    """Service for managing Avaamo sessions"""
    
    @staticmethod
    async def create_session(config) -> Dict:
        """Creates a WebSocket session for agentic agents"""
        url = f"{config.base_url}/web_channel/channel/{config.channel_id}/agentic_agents/create_session"
        
        try:
            payload = {
                "user": {
                    "name": "User",
                    "phone": "9876543210",
                    "email": "qabot@avaamo.com"
                }
            }
            # Include common auth headers for parity with other endpoints
            headers = {
                'Content-Type': 'application/json',
            }

            # Log request details for debugging
            try:
                masked_headers = dict(headers)
                if masked_headers.get('Access-Token'):
                    masked_headers['Access-Token'] = masked_headers['Access-Token'][:4] + "***" + masked_headers['Access-Token'][-3:]
                Logger.info("📤 Creating session (HTTP POST)")
                Logger.info(f"URL: {url}")
                Logger.info(f"Base URL: {getattr(config, 'base_url', '-')}")
                Logger.info(f"Channel ID: {getattr(config, 'channel_id', '-')}")
                Logger.info(f"Headers: {masked_headers}")
                Logger.info(f"Payload: {payload}")
                Logger.info(f"Timeout (s): {getattr(config, 'timeout', 30000) / 1000}")
            except Exception:
                # Best-effort logging only
                pass

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=config.timeout / 1000  
            )
            
            response.raise_for_status()
            Logger.success('✅ Successfully created session')
            
            return {
                'success': True,
                'data': response.json(),
                'channel_id': config.channel_id,
                'timestamp': Logger._timestamp()
            }
            
        except requests.exceptions.RequestException as error:
            Logger.error('❌ Error creating session:', str(error))
            
            if hasattr(error, 'response') and error.response:
                try:
                    Logger.error(f"Status: {error.response.status_code}")
                    Logger.error(f"Reason: {error.response.reason}")
                    Logger.error(f"Response headers: {dict(error.response.headers)}")
                    # Try JSON first, then text
                    try:
                        Logger.error(f"Response JSON: {error.response.json()}")
                    except Exception:
                        Logger.error(f"Response Text: {error.response.text}")
                except Exception:
                    pass
            else:
                # Log best-effort context
                try:
                    Logger.error(f"Request failed before response. URL: {url}")
                    Logger.error(f"Base URL: {getattr(config, 'base_url', '-')}")
                    Logger.error(f"Channel ID: {getattr(config, 'channel_id', '-')}")
                except Exception:
                    pass
            
            return {
                'success': False,
                'error': str(error),
                'channel_id': config.channel_id,
                'timestamp': Logger._timestamp()
            }
    
    @staticmethod
    async def fetch_conversation(config, conversation_id: Optional[str] = None) -> Dict:
        """Fetches conversation transcript and audio from Avaamo API"""
        from src.utils.conversation import process_conversation_data
        
        conv_id = conversation_id or config.conversation_id
        url = f"{config.base_url}/conversations/{conv_id}/messages.json"
        
        Logger.info(f"Fetching conversation data from: {url}")
        
        try:
            response = requests.get(
                url,
                headers={
                    'Access-Token': config.access_token,
                    'Device-Id': config.device_id,
                    'Content-Type': 'application/json'
                },
                timeout=config.timeout / 1000  # Convert to seconds
            )
            
            response.raise_for_status()
            Logger.success('✅ Successfully fetched conversation data')
            
            # Process the conversation data
            evaluation_result = process_conversation_data(response.json())
            
            return {
                'success': True,
                'data': evaluation_result,
                'conversation_id': conv_id,
                'timestamp': Logger._timestamp()
            }
            
        except requests.exceptions.RequestException as error:
            Logger.error('❌ Error fetching conversation:', str(error))
            
            if hasattr(error, 'response') and error.response:
                Logger.error(f"Status: {error.response.status_code}")
                Logger.error(f"Response: {error.response.text}")
            
            return {
                'success': False,
                'error': str(error),
                'conversation_id': conv_id,
                'timestamp': Logger._timestamp()
            } 