#!/usr/bin/env python3
"""Test Telegram bot connectivity and chat ID verification."""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
load_dotenv(project_root / ".env")

async def test_telegram():
    """Test Telegram bot and chat setup."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False

    if not channel_id:
        print("❌ TELEGRAM_CHANNEL_ID not found in .env")
        return False

    print(f"✓ Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
    print(f"✓ Channel ID: {channel_id}")

    # Test 1: Get bot info
    print("\n🤖 Testing bot connectivity...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getMe"
            )
            data = response.json()

            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"✓ Bot name: @{bot_info.get('username', 'N/A')}")
                print(f"✓ Bot ID: {bot_info.get('id')}")
            else:
                print(f"❌ Bot error: {data.get('description')}")
                return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

    # Test 2: Try to send test message
    print("\n📨 Testing message send...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": int(channel_id),
                    "text": "🧪 Telegram integration test successful!",
                },
                timeout=10.0,
            )
            data = response.json()

            if data.get("ok"):
                print(f"✓ Message sent successfully!")
                print(f"  Message ID: {data.get('result', {}).get('message_id')}")
                return True
            else:
                error = data.get("description", "Unknown error")
                print(f"❌ Send failed: {error}")
                print("\n💡 Troubleshooting:")
                print("   1. Make sure bot is added to the chat/channel")
                print("   2. Verify TELEGRAM_CHANNEL_ID is correct")
                print("   3. For groups: use negative ID like -1001234567890")
                print("   4. For private chats: use your user ID")
                return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_telegram())
    sys.exit(0 if result else 1)
