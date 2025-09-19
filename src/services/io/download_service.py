"""
Download Service - Handles downloading audio files from URLs
"""
import asyncio
import aiohttp
import os
import requests
from pathlib import Path
from typing import Dict, List
from src.utils.logger import Logger
from src.models.types import PATHS, DEFAULTS

class DownloadService:
    """Service for downloading audio files"""
    
    @staticmethod
    def clear_audio_directory():
        """Clear all files in the audio steps directory"""
        try:
            # Ensure directory exists
            PATHS.AUDIO_STEPS.mkdir(parents=True, exist_ok=True)
            
            # Get all files in the directory
            audio_files = list(PATHS.AUDIO_STEPS.glob("*.mp3"))
            
            if audio_files:
                
                # Remove each file
                for file_path in audio_files:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        Logger.warning(f"⚠️ Could not remove {file_path.name}: {e}")
                
                Logger.success(f"✅ Cleared {len(audio_files)} existing audio files")
            else:
                Logger.info("📁 Audio directory is already empty")
                
        except Exception as error:
            Logger.error(f"❌ Error clearing audio directory: {error}")
    
    @staticmethod
    async def download_audio_file(audio_url: str, step_name: str, config) -> Dict:
        """Download a single audio file"""
        try:
            # Create downloads directory if it doesn't exist
            PATHS.AUDIO_STEPS.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = f"{step_name}.mp3"
            file_path = PATHS.AUDIO_STEPS / filename
            
            Logger.info(f"📥 Downloading {step_name}")
            
            # Download the file
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            
            # Save the file
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            Logger.success(f"✅ Downloaded {step_name} ({file_size} bytes)")
            
            return {
                'success': True,
                'step': step_name,
                'filePath': str(file_path),
                'size': file_size,
                'url': audio_url,
                'timestamp': Logger._timestamp()
            }
            
        except Exception as error:
            Logger.error(f"❌ Failed to download {step_name}:", str(error))
            return {
                'success': False,
                'step': step_name,
                'error': str(error),
                'url': audio_url,
                'timestamp': Logger._timestamp()
            }
    
    @staticmethod
    async def download_all_step_audio(step_audio: Dict, config) -> List[Dict]:
        """Download all step audio files"""
        download_results = []
        total_steps = len(step_audio)
        
        # Clear existing audio files before downloading new ones
        DownloadService.clear_audio_directory()
        
        Logger.info(f"📥 Starting download of {total_steps} audio files...")
        
        for step_name, step_data in step_audio.items():
            if step_data.get('audio_url'):
                result = await DownloadService.download_audio_file(
                    step_data['audio_url'],
                    step_name,
                    config
                )
                download_results.append(result)
                
                # Show progress
                current = len(download_results)
                Logger.progress(current, total_steps, f"Downloaded {current}/{total_steps}")
            else:
                Logger.warning(f"⚠️ No audio URL found for {step_name}")
                download_results.append({
                    'success': False,
                    'step': step_name,
                    'error': 'No audio URL available',
                    'timestamp': Logger._timestamp()
                })
        
        Logger.success(f"✅ Download completed: {len([r for r in download_results if r['success']])}/{total_steps} successful")
        return download_results 