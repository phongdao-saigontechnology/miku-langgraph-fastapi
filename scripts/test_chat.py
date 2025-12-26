#!/usr/bin/env python3
"""Quick Chat API Test Script."""

import json
import sys
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

BASE_URL = "http://localhost:8100"


def api_call(endpoint, method="GET", data=None, token=None, form=False):
    """Make API call."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req_data = None
    if data:
        if form:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            req_data = urlencode(data).encode()
        else:
            headers["Content-Type"] = "application/json"
            req_data = json.dumps(data).encode()
    
    req = Request(f"{BASE_URL}{endpoint}", method=method, headers=headers, data=req_data)
    
    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"❌ Error {e.code}: {e.read().decode()}")
        return None


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "Hello! Who are you?"
    
    print("=" * 50)
    print("🤖 MIKU CHAT TEST")
    print("=" * 50)
    
    # 1. Register user
    test_id = uuid.uuid4().hex[:8]
    email = f"test_{test_id}@example.com"
    password = f"TestPass123!_{test_id}"
    
    print(f"\n📝 Registering: {email}")
    result = api_call("/api/v1/auth/register", "POST", {"email": email, "password": password})
    if not result:
        sys.exit(1)
    
    user_token = result.get("token", {}).get("access_token")
    print("✅ Registered")
    
    # 2. Create session
    print("\n🔑 Creating session...")
    result = api_call("/api/v1/auth/session", "POST", {}, token=user_token)
    if not result:
        sys.exit(1)
    
    session_id = result["session_id"]
    session_token = result["token"]["access_token"]
    print(f"✅ Session: {session_id[:8]}...")
    
    # 3. Chat
    print(f"\n💬 Sending: {message}")
    print("-" * 50)
    
    result = api_call(
        "/api/v1/chatbot/chat",
        "POST",
        {"messages": [{"role": "user", "content": message}], "session_id": session_id},
        token=session_token
    )
    
    if result:
        for msg in result.get("messages", []):
            if msg["role"] == "assistant":
                print(f"\n🤖 Miku:\n{msg['content']}")
        print("\n" + "=" * 50)
        print("✅ Chat test successful!")
    else:
        print("❌ Chat failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

