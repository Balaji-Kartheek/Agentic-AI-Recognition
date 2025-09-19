#!/usr/bin/env python3
"""
Test script to verify the Python suite components work correctly
"""
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from config.config import config
        print("✅ Config module imported successfully")
        
        from src.models.types import PATHS, DEFAULTS
        print("✅ Types module imported successfully")
        
        from src.utils.logger import Logger
        print("✅ Logger module imported successfully")
        
        from src.utils.conversation import ConversationHistory, process_conversation_data
        print("✅ Conversation module imported successfully")
        
        from src.services.session_service import SessionService
        print("✅ Session service imported successfully")
        
        from src.services.download_service import DownloadService
        print("✅ Download service imported successfully")
        
        from src.services.websocket_service import WebSocketService
        print("✅ WebSocket service imported successfully")
        
        from src.services.audio_service import AudioService
        print("✅ Audio service imported successfully")
        
        from src.services.openai_service import OpenAIService
        print("✅ OpenAI service imported successfully")
        
        from src.services.test_results_service import TestResultsService
        print("✅ Test results service imported successfully")
        
        from src.app import AvaamoAudioEvaluator
        print("✅ Main app imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from config.config import config
        
        print(f"✅ Config loaded:")
        print(f"   - Base URL: {config.base_url}")
        print(f"   - Channel ID: {config.channel_id}")
        print(f"   - LLM Model: {config.llm_model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_logger():
    """Test logger functionality"""
    try:
        from src.utils.logger import Logger
        
        Logger.info("Test info message")
        Logger.success("Test success message")
        Logger.warning("Test warning message")
        Logger.error("Test error message")
        
        print("✅ Logger test completed")
        return True
        
    except Exception as e:
        print(f"❌ Logger test failed: {e}")
        return False

def test_paths():
    """Test path utilities"""
    try:
        from src.models.types import PATHS
        
        print(f"✅ Paths initialized:")
        print(f"   - Base dir: {PATHS.BASE_DIR}")
        print(f"   - Audio steps: {PATHS.AUDIO_STEPS}")
        print(f"   - Logs: {PATHS.LOGS}")
        print(f"   - Test results: {PATHS.TEST_RESULTS}")
        
        return True
        
    except Exception as e:
        print(f"❌ Paths test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Python Suite Components")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Logger", test_logger),
        ("Path Utilities", test_paths),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Python suite is ready to use.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 