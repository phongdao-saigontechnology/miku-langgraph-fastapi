#!/usr/bin/env python3
"""API Test Script - Run after code updates to verify the API is working."""

import argparse
import json
import sys
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode


def make_request(
    url: str, 
    method: str = "GET", 
    data: dict = None, 
    headers: dict = None,
    form_data: bool = False
) -> dict:
    """Make an HTTP request and return the response."""
    headers = headers or {}
    
    req_data = None
    if data:
        if form_data:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            req_data = urlencode(data).encode("utf-8")
        else:
            headers["Content-Type"] = "application/json"
            req_data = json.dumps(data).encode("utf-8")
    
    req = Request(url, method=method, headers=headers, data=req_data)
    
    try:
        with urlopen(req, timeout=120) as response:
            return {
                "status": response.status,
                "data": json.loads(response.read().decode("utf-8")),
                "success": True,
            }
    except HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            body = json.loads(body)
        except:
            pass
        return {
            "status": e.code,
            "data": body,
            "success": False,
            "error": str(e),
        }
    except URLError as e:
        return {
            "status": 0,
            "data": None,
            "success": False,
            "error": str(e.reason),
        }
    except Exception as e:
        return {
            "status": 0,
            "data": None,
            "success": False,
            "error": str(e),
        }


def test_health(base_url: str) -> bool:
    """Test the health endpoint."""
    print("\n🏥 Testing Health Endpoint...")
    print("-" * 40)
    
    result = make_request(f"{base_url}/health")
    
    if result["success"]:
        data = result["data"]
        print(f"✅ Status: {data.get('status', 'unknown')}")
        print(f"   Version: {data.get('version', 'unknown')}")
        print(f"   Environment: {data.get('environment', 'unknown')}")
        components = data.get("components", {})
        for comp, status in components.items():
            icon = "✅" if status == "healthy" else "❌"
            print(f"   {icon} {comp}: {status}")
        return data.get("status") == "healthy"
    else:
        print(f"❌ Health check failed: {result.get('error', 'Unknown error')}")
        return False


def test_root(base_url: str) -> bool:
    """Test the root endpoint."""
    print("\n🏠 Testing Root Endpoint...")
    print("-" * 40)
    
    result = make_request(base_url)
    
    if result["success"]:
        data = result["data"]
        print(f"✅ Message: {data.get('message', 'OK')}")
        print(f"   Version: {data.get('version', 'unknown')}")
        return True
    else:
        print(f"❌ Root endpoint failed: {result.get('error', 'Unknown error')}")
        return False


def setup_auth(base_url: str) -> tuple:
    """Setup authentication by registering/logging in and creating a session."""
    print("\n🔐 Setting Up Authentication...")
    print("-" * 40)
    
    # Generate unique test credentials
    test_id = uuid.uuid4().hex[:8]
    email = f"test_{test_id}@example.com"
    password = f"TestPass123!_{test_id}"
    
    # Try to register
    print(f"   Registering user: {email}")
    register_result = make_request(
        f"{base_url}/api/v1/auth/register",
        method="POST",
        data={"email": email, "password": password},
    )
    
    user_token = None
    if register_result["success"]:
        user_token = register_result["data"].get("token", {}).get("access_token")
        print(f"✅ User registered successfully")
    elif register_result["status"] == 400:
        # User might already exist, try login
        print("   User exists, trying login...")
        login_result = make_request(
            f"{base_url}/api/v1/auth/login",
            method="POST",
            data={"username": email, "password": password, "grant_type": "password"},
            form_data=True,
        )
        if login_result["success"]:
            user_token = login_result["data"].get("access_token")
            print(f"✅ Logged in successfully")
        else:
            print(f"❌ Login failed: {login_result.get('error', 'Unknown')}")
            return None, None
    else:
        print(f"❌ Registration failed: {register_result.get('data', register_result.get('error'))}")
        return None, None
    
    if not user_token:
        print("❌ No user token obtained")
        return None, None
    
    # Create a session
    print("   Creating chat session...")
    session_result = make_request(
        f"{base_url}/api/v1/auth/session",
        method="POST",
        data={},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    
    if session_result["success"]:
        session_data = session_result["data"]
        session_id = session_data.get("session_id")
        session_token = session_data.get("token", {}).get("access_token")
        print(f"✅ Session created: {session_id[:8]}...")
        return session_token, session_id
    else:
        print(f"❌ Session creation failed: {session_result.get('error', 'Unknown')}")
        return None, None


def test_chat(base_url: str, token: str, session_id: str, message: str = "Hello, can you tell me who you are?") -> bool:
    """Test the chat endpoint."""
    print("\n💬 Testing Chat Endpoint...")
    print("-" * 40)
    print(f"   Message: {message}")
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    payload = {
        "messages": [
            {"role": "user", "content": message}
        ],
        "session_id": session_id or str(uuid.uuid4()),
    }
    
    start_time = time.time()
    result = make_request(
        f"{base_url}/api/v1/chatbot/chat",
        method="POST",
        data=payload,
        headers=headers,
    )
    elapsed = time.time() - start_time
    
    if result["success"]:
        data = result["data"]
        messages = data.get("messages", [])
        
        print(f"✅ Chat response received in {elapsed:.2f}s")
        
        # Find assistant response
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Truncate long responses
                if len(content) > 300:
                    content = content[:300] + "..."
                print(f"   Response: {content}")
                return True
        
        print("⚠️  No assistant response found in messages")
        print(f"   Raw response: {data}")
        return False
    else:
        print(f"❌ Chat failed (HTTP {result.get('status', '?')})")
        detail = result.get("data", result.get("error", "Unknown"))
        if isinstance(detail, dict):
            detail = detail.get("detail", detail)
        print(f"   Error: {str(detail)[:300]}")
        return False


def test_chat_stream(base_url: str, token: str, session_id: str, message: str = "Count from 1 to 5") -> bool:
    """Test the streaming chat endpoint."""
    print("\n🌊 Testing Chat Stream Endpoint...")
    print("-" * 40)
    print(f"   Message: {message}")
    
    try:
        import urllib.request
        
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        payload = {
            "messages": [
                {"role": "user", "content": message}
            ],
            "session_id": session_id or str(uuid.uuid4()),
        }
        
        req = urllib.request.Request(
            f"{base_url}/api/v1/chatbot/chat/stream",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=120) as response:
            content = b""
            for chunk in iter(lambda: response.read(100), b""):
                content += chunk
                if len(content) > 500:
                    break
            
            elapsed = time.time() - start_time
            
            if content:
                print(f"✅ Stream response received in {elapsed:.2f}s")
                preview = content.decode("utf-8", errors="ignore").replace("\n", " ")[:150]
                print(f"   Preview: {preview}...")
                return True
            else:
                print("⚠️  Empty stream response")
                return False
                
    except Exception as e:
        print(f"❌ Stream test failed: {str(e)}")
        return False


def run_tests(base_url: str, test_message: str = None, skip_chat: bool = False, test_stream: bool = False) -> bool:
    """Run all API tests."""
    print("=" * 50)
    print("🧪 MIKU API TEST SUITE")
    print("=" * 50)
    print(f"Base URL: {base_url}")
    
    results = {}
    
    # Test health
    results["health"] = test_health(base_url)
    
    # Test root
    results["root"] = test_root(base_url)
    
    if not skip_chat:
        # Setup auth (register + create session)
        token, session_id = setup_auth(base_url)
        results["auth"] = token is not None
        
        if token:
            # Test chat
            msg = test_message or "Hello! Please introduce yourself briefly. Who are you and what can you do?"
            results["chat"] = test_chat(base_url, token, session_id, msg)
            
            # Test stream (optional)
            if test_stream:
                results["stream"] = test_chat_stream(base_url, token, session_id, "Say hello in exactly 5 words")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        icon = "✅" if passed else "❌"
        status = "PASSED" if passed else "FAILED"
        print(f"   {icon} {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed!")
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Test the Miku API endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_api.py                    # Run all tests
  python scripts/test_api.py --skip-chat        # Quick health check only
  python scripts/test_api.py -m "Hello Miku!"   # Custom chat message
  python scripts/test_api.py --stream           # Include streaming test
  python scripts/test_api.py -w 10              # Wait 10s before testing
        """
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8100",
        help="Base URL of the API (default: http://localhost:8100)",
    )
    parser.add_argument(
        "--message", "-m",
        default=None,
        help="Custom message to send to chat endpoint",
    )
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Skip chat endpoint tests (useful for quick health checks)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Also test the streaming endpoint",
    )
    parser.add_argument(
        "--wait", "-w",
        type=int,
        default=0,
        help="Wait N seconds before running tests (for container startup)",
    )
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for services to start...")
        time.sleep(args.wait)
    
    success = run_tests(args.url, args.message, args.skip_chat, args.stream)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
