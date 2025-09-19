#!/usr/bin/env python3
"""
Simple run script for the Python suite
"""
import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def run_suite():
    """Run the Python suite"""
    try:
        from config.config import config
        from src.app import AvaamoAudioEvaluator
        
        print("🚀 Starting Python Suite...")
        
        # Create and run the application
        app = AvaamoAudioEvaluator(config)
        result = await app.run()
        
        # Handle multi-conversation results
        if hasattr(config, 'conversation_ids') and len(config.conversation_ids) > 1:
            if result.get('success'):
                print(f"\n🎉 Multi-conversation execution completed!")
                print(f"✅ Successful: {result.get('successful', 0)}/{result.get('total_conversations', 0)}")
                print(f"❌ Failed: {result.get('failed', 0)}/{result.get('total_conversations', 0)}")
                return 0
            else:
                print(f"❌ Multi-conversation execution failed: {result.get('error', 'Unknown error')}")
                return 1
        else:
            # Single conversation mode
            if result.get('success'):
                print("✅ Python suite completed successfully!")
                return 0
            else:
                print(f"❌ Python suite failed: {result.get('error', 'Unknown error')}")
                return 1
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you have installed all dependencies:")
        print("   pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_suite())
    sys.exit(exit_code) 