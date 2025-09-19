"""
Dynamic Run Service - Handles LLM-based conversation step generation and audio synthesis
"""
import asyncio
from pathlib import Path
from typing import Dict, List
import json

from src.models.types import PATHS
from src.services.evaluation.openai_service import OpenAIService
from src.services.tts.google_tts_service import GoogleTTSService
from src.utils.logger import Logger


class DynamicRunService:
    """Service for generating dynamic conversation steps and audio files"""

    @staticmethod
    async def generate_conversation_steps(
        scenario: str, 
        max_steps: int, 
        openai_api_key: str,
        llm_model: str = 'gpt-4o',
        temperature: float = 0.3
    ) -> Dict:
        """Generate conversation steps using LLM based on scenario"""
        try:
            llm = OpenAIService({
                'api_key': openai_api_key,
                'model': llm_model,
                'temperature': temperature
            })

            prompt = f"""
Generate {max_steps} conversation steps for a phone call scenario: "{scenario}"

Requirements:
- Start with "I want to confirm the appointment" or similar opening
- Each step should be a natural, concise user utterance
- Steps should progress logically through the conversation
- Keep each step under 50 words
- Make it sound like a real person calling

Return ONLY a JSON array of strings, one per step. Example:
["I want to confirm my appointment", "My name is John Doe", "My date of birth is January 1st, 1990"]

Generate exactly {max_steps} steps:
"""

            # Use the existing OpenAI service to generate steps
            completion = await llm.openai.chat.completions.create(
                model=llm.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a conversation designer. Generate natural, realistic user utterances for phone calls. Return only valid JSON arrays."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=llm.temperature,
                max_tokens=500
            )

            response_text = completion.choices[0].message.content.strip()
            
            # Try to parse JSON from response
            try:
                steps = json.loads(response_text)
                if isinstance(steps, list) and len(steps) > 0:
                    # Ensure we have the right number of steps
                    if len(steps) > max_steps:
                        steps = steps[:max_steps]
                    elif len(steps) < max_steps:
                        # Pad with generic steps if needed
                        while len(steps) < max_steps:
                            steps.append("Thank you, that's all I needed.")
                    
                    return {
                        "success": True,
                        "steps": steps,
                        "count": len(steps)
                    }
                else:
                    raise ValueError("Invalid steps format")
                    
            except json.JSONDecodeError:
                # Fallback: try to extract steps from text
                Logger.warning("Failed to parse JSON, attempting text extraction...")
                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                steps = []
                for line in lines:
                    # Remove numbering and quotes
                    clean_line = line.lstrip('0123456789.- ').strip('"\'')
                    if clean_line and len(clean_line) > 5:
                        steps.append(clean_line)
                        if len(steps) >= max_steps:
                            break
                
                if steps:
                    return {
                        "success": True,
                        "steps": steps[:max_steps],
                        "count": len(steps[:max_steps])
                    }
                else:
                    raise ValueError("Could not extract steps from response")

        except Exception as error:
            Logger.error(f"❌ Error generating conversation steps: {error}")
            return {
                "success": False,
                "error": str(error)
            }

    @staticmethod
    async def generate_audio_from_steps(
        steps: List[str],
        output_dir: Path = None
    ) -> Dict:
        """Convert conversation steps to audio files"""
        try:
            if output_dir is None:
                output_dir = PATHS.DYNAMIC_VOICES
            
            # Clear existing files
            for file in output_dir.glob("*.wav"):
                file.unlink()
            
            # Generate audio using Google TTS
            tts = GoogleTTSService(language="en", tld="com", min_duration=8.0, sample_rate=24000)
            output_paths = await tts.synthesize(steps, output_dir)
            
            return {
                "success": True,
                "count": len(output_paths),
                "files": [str(p) for p in output_paths],
                "steps": steps
            }
            
        except Exception as error:
            Logger.error(f"❌ Error generating audio from steps: {error}")
            return {
                "success": False,
                "error": str(error)
            }

    @staticmethod
    async def generate_dynamic_conversation(
        scenario: str,
        max_steps: int,
        openai_api_key: str,
        llm_model: str = 'gpt-4o',
        temperature: float = 0.3
    ) -> Dict:
        """Complete workflow: generate steps and convert to audio"""
        try:
            Logger.info(f"🎯 Generating dynamic conversation for scenario: {scenario}")
            
            # Step 1: Generate conversation steps
            steps_result = await DynamicRunService.generate_conversation_steps(
                scenario, max_steps, openai_api_key, llm_model, temperature
            )
            
            if not steps_result.get("success"):
                return steps_result
            
            steps = steps_result["steps"]
            Logger.success(f"✅ Generated {len(steps)} conversation steps")
            
            # Step 2: Convert to audio
            audio_result = await DynamicRunService.generate_audio_from_steps(steps)
            
            if not audio_result.get("success"):
                return audio_result
            
            Logger.success(f"✅ Generated {audio_result['count']} audio files")
            
            return {
                "success": True,
                "steps": steps,
                "audio_files": audio_result["files"],
                "count": len(steps)
            }
            
        except Exception as error:
            Logger.error(f"❌ Error in dynamic conversation generation: {error}")
            return {
                "success": False,
                "error": str(error)
            }

    @staticmethod
    async def run_dynamic_conversation(
        websocket,
        conversation_history,
        scenario: str,
        max_steps: int,
        openai_api_key: str,
        llm_model: str = 'gpt-4o',
        temperature: float = 0.3
    ) -> List[Dict]:
        """Run dynamic conversation in real-time using conversation context"""
        try:
            Logger.info(f"🎯 Starting dynamic conversation for scenario: {scenario}")
            
            # Initialize LLM and TTS
            llm = OpenAIService({
                'api_key': openai_api_key,
                'model': llm_model,
                'temperature': temperature
            })
            # Default to Google TTS for dynamic unless replaced later via config; keeping current behavior
            tts = GoogleTTSService(language="en", tld="com", min_duration=18.0, sample_rate=24000)
            
            audio_results = []
            conversation_context = ""
            step_count = 0
            
            # Helper to detect repeated agent prompt
            def is_repeated_agent_prompt(current: str, previous: str) -> bool:
                if not current or not previous:
                    return False
                a = current.strip().lower()
                b = previous.strip().lower()
                return a == b or (len(a) > 20 and a in b) or (len(b) > 20 and b in a)
            
            last_agent_response = ""
            
            while step_count < max_steps:
                step_count += 1
                Logger.info(f"🔄 Dynamic step {step_count}/{max_steps}")
                
                # Generate next user utterance based on conversation context
                gen_result = await llm.generate_next_user_utterance(
                    scenario=scenario,
                    agent_last_message=last_agent_response,
                    conversation_so_far=conversation_context,
                    remaining_steps=max_steps - step_count + 1,
                    initial_opening=(step_count == 1)
                )
                
                if not gen_result.get('success'):
                    Logger.error(f"❌ Failed to generate utterance at step {step_count}: {gen_result.get('error')}")
                    break
                
                user_utterance = gen_result.get('text', '').strip()
                if not user_utterance:
                    Logger.warning(f"⚠️ Empty utterance generated at step {step_count}; stopping.")
                    break
                
                Logger.info(f"🎤 Generated utterance: {user_utterance}")
                
                # Convert to audio
                temp_dir = PATHS.DYNAMIC_VOICES
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # # Clear previous temp files
                # for temp_file in temp_dir.glob("temp_step_*.wav"):
                #     temp_file.unlink()
                
                Logger.info(f"🎵 Converting utterance to audio...")
                
                # Generate audio for this utterance (one at a time)
                temp_filename = f"temp_step_{step_count}.wav"
                temp_file_path = temp_dir / temp_filename
                
                # Clear any existing files with this name
                if temp_file_path.exists():
                    temp_file_path.unlink()
                
                # Use TTS to generate single audio file directly to our path
                await tts.synthesize_single(user_utterance, temp_file_path)
                audio_file_path = str(temp_file_path)
                
                Logger.info(f"🎵 Audio file created: {audio_file_path}")
                
                # Send audio and wait for response
                from src.services.conversation.audio_service import AudioService
                from src.models.types import DEFAULTS
                
                send_result = await AudioService.send_audio_file_and_wait_for_response(
                    websocket=websocket,
                    file_path=audio_file_path,
                    utterance=user_utterance,
                    timeout=DEFAULTS.RESPONSE_TIMEOUT,
                    conversation_history=conversation_history
                )
                try:
                    from os.path import getsize
                    Logger.debug(f"📄 Sent file size: {getsize(audio_file_path)} bytes for {temp_filename}")
                except Exception:
                    pass
                
                audio_results.append(send_result)
                
                # Update conversation context
                conversation_context += f"\nUser: {user_utterance}\n"
                
                # Extract bot response
                bot_response = send_result.get('botResponse')
                bot_text = ""
                if isinstance(bot_response, dict):
                    bot_text = bot_response.get('response') or bot_response.get('delta') or ""
                elif isinstance(bot_response, str):
                    bot_text = bot_response
                
                conversation_context += f"Agent: {bot_text}\n"
                Logger.info(f"🤖 Bot response: {bot_text}")
                
                # Check for repetition - if agent repeats, don't advance step counter
                if is_repeated_agent_prompt(bot_text, last_agent_response):
                    Logger.info("🔄 Agent repeated a prompt; not advancing step counter.")
                    step_count -= 1  # Retry this step
                else:
                    last_agent_response = bot_text
                
                # Add delay between steps
                await asyncio.sleep(2)
            
            Logger.success(f"✅ Dynamic conversation completed with {len(audio_results)} steps")
            return audio_results
            
        except Exception as error:
            Logger.error(f"❌ Error in dynamic conversation: {error}")
            return [{'success': False, 'error': str(error)}]
