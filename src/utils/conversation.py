"""
Conversation utility for processing conversation data
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.models.types import PATHS

def find_full_call_recording(entries: List[Dict]) -> Optional[Dict]:
    """Find the full call recording (first audio entry with large file size)"""
    for entry in entries:
        if (entry.get('content_type') == 'audio' and 
            entry.get('attachments') and 
            entry['attachments'][0].get('files')):
            
            file = entry['attachments'][0]['files'][0]
            if file and file.get('size', 0) > 1000000:  # Large file (>1MB)
                return {
                    'url': file.get('url'),
                    'size': file.get('size'),
                    'content_type': file.get('content_type'),
                    'name': file.get('name'),
                    'uuid': entry.get('uuid'),
                    'created_at': entry.get('created_at')
                }
    return None

def find_transcript(entries: List[Dict]) -> Optional[str]:
    """Find the transcript text entry"""
    for entry in entries:
        if (entry.get('content_type') == 'text' and 
            entry.get('content') and 
            '*transcript*' in entry['content']):
            return entry['content']
    return None

def extract_user_audio_segments(entries: List[Dict]) -> List[Dict]:
    """Extract user audio segments (smaller segment files)"""
    user_audio_segments = []
    
    for entry in entries:
        if (entry.get('content_type') == 'audio' and 
            entry.get('attachments') and 
            entry['attachments'][0].get('files') and
            entry.get('user', {}).get('phone')):
            
            file = entry['attachments'][0]['files'][0]
            if file and 'segment' in file.get('name', ''):
                user_audio_segments.append({
                    'content': entry.get('content'),
                    'audio_url': file.get('url'),
                    'file_size': file.get('size'),
                    'created_at': entry.get('created_at'),
                    'timetoken': entry.get('timetoken'),
                    'uuid': entry.get('uuid'),
                    'user_phone': entry['user']['phone']
                })
    
    # Sort by timetoken (chronological order)
    return sorted(user_audio_segments, key=lambda x: x.get('timetoken', 0))

def clean_transcript(raw_transcript: str) -> str:
    """Clean transcript by removing system noise and keeping only Agent/User conversation"""
    if not raw_transcript:
        return ''
    
    lines = raw_transcript.split('\n')
    clean_lines = []
    
    for line in lines:
        trimmed_line = line.strip()
        
        # Only keep lines that start with Agent: or User:
        if trimmed_line.startswith('Agent: ') or trimmed_line.startswith('User: '):
            clean_lines.append(trimmed_line)
    
    return '\n'.join(clean_lines)

def parse_transcript_steps(transcript: str) -> List[Dict]:
    """Parse transcript to extract conversation steps"""
    if not transcript:
        return []
    
    # First clean the transcript
    cleaned_transcript = clean_transcript(transcript)
    steps = []
    lines = cleaned_transcript.split('\n')
    
    for line in lines:
        if line.startswith('User: '):
            steps.append({
                'type': 'user',
                'content': line.replace('User: ', '').strip(),
                'step_number': len([s for s in steps if s['type'] == 'user']) + 1
            })
        elif line.startswith('Agent: '):
            steps.append({
                'type': 'agent',
                'content': line.replace('Agent: ', '').strip()
            })
    
    return steps

def build_step_audio(audio_segments: List[Dict], conversation_steps: List[Dict]) -> Dict:
    """Build the step-by-step audio object"""
    step_audio = {}
    user_steps = [step for step in conversation_steps if step['type'] == 'user']
    
    for index, step in enumerate(user_steps):
        if index < len(audio_segments):
            corresponding_audio = audio_segments[index]
            step_audio[f"step_{step['step_number']}"] = {
                'audio_url': corresponding_audio['audio_url'],
                'utterance': step['content']
            }
    
    return step_audio

def process_conversation_data(api_data: Dict) -> Dict:
    """Process conversation data to extract audio and transcript information"""
    entries = api_data.get('entries', [])
    
    full_call_recording = find_full_call_recording(entries)
    raw_transcript = find_transcript(entries)
    cleaned_transcript = clean_transcript(raw_transcript)
    user_audio_segments = extract_user_audio_segments(entries)
    conversation_steps = parse_transcript_steps(raw_transcript)
    step_audio = build_step_audio(user_audio_segments, conversation_steps)
    
    return {
        'full_audio_url': full_call_recording['url'] if full_call_recording else None,
        'transcript': cleaned_transcript,
        'step_audio': step_audio
    }

def extract_step_audio(api_data: Dict) -> Dict:
    """Extract step audio from conversation data for simplified access"""
    processed = process_conversation_data(api_data)
    return processed['step_audio']

class ConversationHistory:
    """Logs conversation history to file"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        self.filename = f"conversation_history_{conversation_id}_{self.timestamp}.txt"
        self.filepath = PATHS.LOGS / self.filename
        
        # Ensure logs directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write header
        header = (f"Conversation History\n"
                 f"Conversation ID: {conversation_id}\n"
                 f"Started: {datetime.now().isoformat()}\n"
                 f"{'='*50}\n\n")
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write(header)
    
    def log(self, speaker: str, message: str):
        """Log a message to the conversation history file"""
        timestamp = datetime.now().isoformat()
        entry = f"[{timestamp}] {speaker}: {message}\n\n"
        
        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            print(f'❌ Error writing to conversation history: {e}') 