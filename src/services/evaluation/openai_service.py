"""
OpenAI Service - Handles LLM-based conversation evaluation
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from src.utils.logger import Logger

class OpenAIService:
    """Service for OpenAI API integration and conversation evaluation"""
    
    def __init__(self, options: Dict[str, Any]):
        api_key = options.get('api_key')
        model = options.get('model')
        temperature = options.get('temperature')
        
        if not api_key:
            raise ValueError('OpenAI API key is required')
        
        self.model = model or 'gpt-4o'
        self.temperature = float(temperature) if temperature is not None else 0.2
        
        self.openai = AsyncOpenAI(
            api_key=api_key
        )
    
    async def evaluate_conversation(
        self, 
        actual_transcript: str, 
        golden_transcript: str, 
        test_id: str, 
        channel_id: str,
        run_type: str = "human",
        scenario: Optional[str] = None
    ) -> Dict:
        """Evaluate if the actual conversation followed the golden conversation path"""
        try:
            Logger.info('🔍 Starting LLM conversation evaluation...')
            # Logger.info(
            #     f"""
            #     actual_transcript: {actual_transcript}
            #     golden_transcript: {golden_transcript}
            #     test_id: {test_id}
            #     channel_id: {channel_id}
            #     run_type: {run_type}
            #     scenario: {scenario}
            #     """
            # )
            
            def build_prompt() -> str:
                rt = (run_type or "human").lower()
                if rt == "human":
                    return f"""
GOLDEN CONVERSATION (Expected Path):
{golden_transcript}

ACTUAL CONVERSATION (User Test Run):
{actual_transcript}

Task: Evaluate whether the User run followed the golden conversation path.

STRICT EVALUATION CRITERIA:
1. Logical sequence alignment with golden steps
2. Key information points requested and provided
3. Agent consistency with golden behavior
4. Critical steps missed or added unexpectedly
5. Be strict in evaluation - minor deviations should still be "pass" but major flow changes should be "fail"
6. Keep all text concise and professional.


Return ONLY this JSON:
{{
  "test_id": "{test_id}",
  "channelId": "{channel_id}",
  "scenario": "One-line summary",
  "scenario_result": should be "pass" if the conversation path matched closely, "fail" if it deviated significantly,
  "transcript": "Copy actual transcript here",
  "cover_story": {{
    "failure_reason": "Specific reason if failed, empty string if passed",
    "what_went_well": "What aspects of the conversation worked correctly",
    "what_to_improve": "Specific actionable improvements needed"
  }}
}}"""
                if rt == "synthetic":
                    return f"""
ACTUAL CONVERSATION:
{actual_transcript}

Task: Evaluate the conversation quality without a golden transcript. Focus on whether the conversation logically progressed and completed the user's request effectively.

STRICT EVALUATION CRITERIA:
1. Goal completion with required confirmations/information
2. Coherence and forward progression (avoid loops or derailments)
3. Politeness, appropriateness, and safety adherence
4. Efficiency (keep unnecessary back-and-forth minimal)

Return ONLY this JSON:
{{
  "test_id": "{test_id}",
  "channelId": "{channel_id}",
  "scenario": "One-line summary",
  "scenario_result": "pass",
  "transcript": "Copy actual transcript here",
  "cover_story": {{
    "failure_reason": "If failed, explain precisely; else empty",
    "what_went_well": "Brief bullets",
    "what_to_improve": "Actionable bullets"
  }}
}}"""
                if rt == "dynamic":
                    return f"""
SCENARIO: {scenario or "Unknown"}

ACTUAL CONVERSATION:
{actual_transcript}

Task: Evaluate whether the conversation successfully accomplished the scenario intent using an efficient, natural dialog. No golden transcript exists.

STRICT EVALUATION CRITERIA:
1. Goal completion with required confirmations/information
2. Coherence and progression toward the scenario
3. Appropriateness and safety policy adherence
4. Efficiency (no unnecessary loops or derailments)
5. Be strict in evaluation - minor deviations should still be "pass" but major flow changes should be "fail"
6. Keep all text concise and professional.

Return ONLY this JSON:
{{
  "test_id": "{test_id}",
  "channelId": "{channel_id}",
  "scenario": "One-line summary",
  "scenario_result": should be "pass" if the conversation path matched closely, "fail" if it deviated significantly,
  "transcript": "Copy actual transcript here",
  "cover_story": {{
    "failure_reason": "Specific reason if failed, empty string if passed",
    "what_went_well": "What aspects of the conversation worked correctly",
    "what_to_improve": "Specific actionable improvements needed"
  }}
}}"""
                if rt == "translation":
                    return f"""
ACTUAL CONVERSATION (Translated/Non-English context):
{actual_transcript}

Task: Evaluate conversation quality without a golden transcript. Focus on task completion and language clarity.

STRICT EVALUATION CRITERIA:
1. Intent understanding and task completion
2. Language correctness and clarity (assess based on the provided text transcript)
3. Appropriate responses and safety
4. Efficiency and lack of repetition

Return ONLY this JSON:
{{
  "test_id": "{test_id}",
  "channelId": "{channel_id}",
  "scenario": "One-line summary",
  "scenario_result": "pass",
  "transcript": "Copy actual transcript here",
  "cover_story": {{
    "failure_reason": "Specific reason if failed, empty string if passed",
    "what_went_well": "What aspects of the conversation worked correctly",
    "what_to_improve": "Specific actionable improvements needed"
  }}
}}"""

            prompt = build_prompt()

            completion = await self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert QA conversation analyst. Evaluate conversation paths with precision and provide results in exact JSON format. Be strict but fair in your evaluation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent, deterministic results
                max_tokens=1000
            )

            evaluation_text = completion.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            evaluation_result = None
            try:
                # First, try parsing as-is
                evaluation_result = json.loads(evaluation_text)
                
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text
                Logger.info('🔧 Attempting to extract JSON from LLM response...')
                
                try:
                    # Look for JSON block between { and }
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', evaluation_text)
                    if json_match:
                        evaluation_result = json.loads(json_match.group(0))
                        Logger.info('✅ Successfully extracted JSON from response')
                    else:
                        raise ValueError('No JSON block found in response')
                except Exception as extract_error:
                    Logger.error('❌ Failed to parse evaluation JSON:', str(extract_error))
                    Logger.error('❌ Failed to extract JSON:', str(extract_error))
                    Logger.error('Raw response:', evaluation_text[:500] + '...')
                    
                    # Fallback result if JSON parsing fails
                    return {
                        'success': False,
                        'error': 'Failed to parse evaluation response',
                        'fallback_result': {
                            'test_id': test_id,
                            'channelId': channel_id,
                            'scenario': "Evaluation parsing failed",
                            'scenario_result': "fail",
                            'transcript': actual_transcript,
                            'golden_transcript': golden_transcript,
                            'cover_story': {
                                'failure_reason': "LLM evaluation response could not be parsed",
                                'what_went_well': "Audio files were sent successfully",
                                'what_to_improve': "Fix evaluation response parsing"
                            }
                        },
                        'raw_response': evaluation_text
                    }
            
            # Ensure the transcript is properly set
            if not evaluation_result.get('transcript') or evaluation_result['transcript'] == "Copy the actual conversation transcript here":
                evaluation_result['transcript'] = actual_transcript

            # Add the golden transcript only for human runs
            if (run_type or "human").lower() == "human":
                evaluation_result['golden_transcript'] = golden_transcript
            else:
                evaluation_result['golden_transcript'] = ""
            
            Logger.success('✅ LLM evaluation completed successfully')
            
            return {
                'success': True,
                'result': evaluation_result,
                'usage': completion.usage.model_dump() if completion.usage else None,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as error:
            Logger.error('❌ LLM Evaluation Error:', str(error))
            
            # Fallback result if API call fails
            return {
                'success': False,
                'error': str(error),
                'fallback_result': {
                    'test_id': test_id,
                    'channelId': channel_id,
                    'scenario': "LLM evaluation failed",
                    'scenario_result': "fail", 
                    'transcript': actual_transcript,
                    'golden_transcript': golden_transcript,
                    'cover_story': {
                        'failure_reason': f"LLM API error: {error}",
                        'what_went_well': "Audio files were sent and conversation was logged",
                        'what_to_improve': "Fix LLM API connection and retry evaluation"
                    }
                },
                'timestamp': datetime.now().isoformat()
            } 

    async def generate_next_user_utterance(
        self,
        scenario: str,
        agent_last_message: Optional[str],
        conversation_so_far: Optional[str],
        remaining_steps: int,
        initial_opening: bool = False
    ) -> Dict[str, Any]:
        """Generate the next User utterance for dynamic synthetic flow."""
        try:
            system_prompt = (
                "You are the QA caller in a phone call. Speak concisely in natural phrases. "
                "Goal: " + scenario + ". "
                "Respond only with what the caller would say next. Do not include narration. "
                "If the agent repeats the same verification question, repeat or clarify succinctly rather than introducing new information. "
                "Never acknowledge you are an AI."
            )

            if initial_opening:
                # For the first response after greeting, always start with the scenario
                user_prompt = f"Agent greeted you. Start the conversation by saying you want to {scenario.lower()}. Keep it brief and natural."
            else:
                user_prompt = (
                    (f"Agent said: {agent_last_message}\n" if agent_last_message else "") +
                    (f"Conversation so far:\n{conversation_so_far}\n" if conversation_so_far else "") +
                    f"You have {remaining_steps} step(s) remaining. Keep it brief and move forward."
                )

            completion = await self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=120
            )

            text = (completion.choices[0].message.content or "").strip()
            return {"success": True, "text": text}
        except Exception as error:
            Logger.error('❌ LLM next-utterance error:', str(error))
            return {"success": False, "error": str(error)}