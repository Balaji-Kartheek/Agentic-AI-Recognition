"""
Entry Point - Avaamo Agentic Audio Evaluator
"""
import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.config import config
from src.app import AvaamoAudioEvaluator

async def main():
    """Main entry point"""
    try:
        app = AvaamoAudioEvaluator(config)
        result = await app.run()
        
        # Handle multi-conversation results
        if hasattr(config, 'conversation_ids') and len(config.conversation_ids) > 1:
            if result.get('success'):
                print(f"\n🎉 Multi-conversation execution completed!")
                print(f"✅ Successful: {result.get('successful', 0)}/{result.get('total_conversations', 0)}")
                print(f"❌ Failed: {result.get('failed', 0)}/{result.get('total_conversations', 0)}")
            else:
                print(f"❌ Multi-conversation execution failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        else:
            # Single conversation mode
            if not result.get('success'):
                print(f"❌ Application failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Application interrupted by user")
        sys.exit(0)
    except Exception as error:
        print(f"💥 Unexpected error: {error}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 