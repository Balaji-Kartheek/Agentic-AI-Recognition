"""
Test Results Service - Handles test result processing and evaluation
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import Logger
from src.models.types import PATHS

class TestResultsService:
    """Service for managing test results and evaluation data"""
    
    @staticmethod
    def generate_test_id(conversation_id: str) -> str:
        """Generate a unique test ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"test_{conversation_id}_{timestamp}"
    
    @staticmethod
    def read_conversation_history(file_path: str) -> Optional[str]:
        """Read conversation history from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as error:
            Logger.error(f"❌ Error reading conversation history {file_path}: {error}")
            return None
    
    @staticmethod
    def extract_clean_transcript(content: str) -> str:
        """Extract clean transcript from conversation history content"""
        if not content:
            return ""
        
        lines = content.split('\n')
        transcript_lines = []
        
        # Patterns:
        # 1) With timestamp prefix: [ISO_TS] <Speaker>: text
        # 2) Without timestamp: <Speaker>: text
        # Support speakers used across modes: Agent/User/Target Bot/QA Bot
        speaker_group = r"(Agent|User|Target Bot|QA Bot)"
        ts_pattern = re.compile(rf"^\[[^\]]+\]\s*{speaker_group}:\s*(.+)$")
        plain_pattern = re.compile(rf"^{speaker_group}:\s*(.+)$")
        
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            match = ts_pattern.match(line) or plain_pattern.match(line)
            if match:
                speaker = match.group(1)
                text = match.group(2).strip()
                # Skip boilerplate-only lines if somehow empty after strip
                if text:
                    transcript_lines.append(f"{speaker}: {text}")
        
        return '\n'.join(transcript_lines)
    
    @staticmethod
    def create_test_summary(evaluation_result: Dict, metadata: Dict) -> Dict:
        """Create a comprehensive test summary"""
        timestamp = datetime.now().isoformat()
        
        # Extract key information from evaluation result
        test_summary = {
            'test_id': evaluation_result.get('test_id', 'unknown'),
            'channel_id': evaluation_result.get('channelId', 'unknown'),
            'scenario': evaluation_result.get('scenario', 'Unknown scenario'),
            'scenario_result': evaluation_result.get('scenario_result', 'unknown'),
            'transcript': evaluation_result.get('transcript', ''),
            'golden_transcript': evaluation_result.get('golden_transcript', ''),
            'evaluation_details': {
                'failure_reason': evaluation_result.get('cover_story', {}).get('failure_reason', ''),
                'what_went_well': evaluation_result.get('cover_story', {}).get('what_went_well', ''),
                'what_to_improve': evaluation_result.get('cover_story', {}).get('what_to_improve', '')
            },
            'metadata': {
                'duration_ms': metadata.get('duration', 0),
                'audio_files_sent': metadata.get('audioFilesSent', 0),
                'total_messages': metadata.get('totalMessages', 0),
                'evaluation_model': metadata.get('evaluation_model', 'unknown'),
                'timestamp': timestamp
            }
        }
        
        return test_summary
    
    @staticmethod
    async def save_test_result(test_result: Dict, conversation_id: str) -> Dict:
        """Save test result to file"""
        try:
            # Ensure test results directory exists
            PATHS.TEST_RESULTS.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
            filename = f"test_result_{conversation_id}_{timestamp}.json"
            file_path = PATHS.TEST_RESULTS / filename
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_result, f, indent=2, ensure_ascii=False)
            
            Logger.success(f"✅ Test result saved to: {filename}")
            
            return {
                'success': True,
                'filename': filename,
                'file_path': str(file_path),
                'timestamp': timestamp
            }
            
        except Exception as error:
            Logger.error(f"❌ Failed to save test result: {error}")
            return {
                'success': False,
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def get_test_results_summary() -> Dict:
        """Get a summary of all test results"""
        try:
            test_files = os.path.glob(str(PATHS.TEST_RESULTS / "test_result_*.json"))
            
            if not test_files:
                return {
                    'total_tests': 0,
                    'passed_tests': 0,
                    'failed_tests': 0,
                    'success_rate': 0.0
                }
            
            total_tests = len(test_files)
            passed_tests = 0
            failed_tests = 0
            
            for test_file in test_files:
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                        if test_data.get('scenario_result') == 'pass':
                            passed_tests += 1
                        else:
                            failed_tests += 1
                except Exception:
                    # Skip files that can't be parsed
                    continue
            
            success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            return {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': round(success_rate, 2)
            }
            
        except Exception as error:
            Logger.error(f"❌ Error getting test results summary: {error}")
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'success_rate': 0.0,
                'error': str(error)
            } 