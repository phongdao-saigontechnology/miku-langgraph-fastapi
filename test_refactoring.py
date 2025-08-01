#!/usr/bin/env python3
"""
Test script to verify the channel refactoring worked correctly.
"""

def test_basic_imports():
    """Test that basic classes can be imported."""
    try:
        from app.api.v1.channels import UserMessage, InputChannel, OutputChannel, CollectingOutputChannel
        print("✓ Basic imports successful")
        return True
    except Exception as e:
        print(f"✗ Basic imports failed: {e}")
        return False

def test_utility_functions():
    """Test that utility functions can be imported."""
    try:
        from app.api.v1.channels import decode_jwt, decode_bearer_token, replace_synonyms, on_new_message
        print("✓ Utility functions import successful")
        return True
    except Exception as e:
        print(f"✗ Utility functions import failed: {e}")
        return False

def test_individual_files():
    """Test that individual files can be imported."""
    try:
        from app.api.v1.channels.user_message import UserMessage
        from app.api.v1.channels.input_channel import InputChannel
        from app.api.v1.channels.output_channel import OutputChannel
        from app.api.v1.channels.collecting_output_channel import CollectingOutputChannel
        print("✓ Individual file imports successful")
        return True
    except Exception as e:
        print(f"✗ Individual file imports failed: {e}")
        return False

def test_backward_compatibility():
    """Test that the original channel.py still works."""
    try:
        from app.api.v1.channel import UserMessage, InputChannel, OutputChannel
        print("✓ Backward compatibility successful")
        return True
    except Exception as e:
        print(f"✗ Backward compatibility failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing channel refactoring...")
    print("=" * 40)
    
    tests = [
        test_basic_imports,
        test_utility_functions,
        test_individual_files,
        test_backward_compatibility,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Refactoring successful.")
    else:
        print("❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main() 