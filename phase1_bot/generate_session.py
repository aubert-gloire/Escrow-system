"""
One-time Telethon Session Generator

Run this LOCALLY (not on the server) to authenticate your Telegram user account
and generate a session string that can be stored in your .env / Render environment.

Steps:
    1. Get API_ID and API_HASH from https://my.telegram.org/apps
    2. Run:  python generate_session.py
    3. Enter your phone number and the code Telegram sends you.
    4. Copy the printed TELEGRAM_SESSION_STRING into your .env file.
    5. Add TELEGRAM_API_ID and TELEGRAM_API_HASH to your .env file too.

The session string replaces a session file and works in cloud environments (Render, etc).
You only need to run this once. The session stays valid indefinitely unless you
terminate it from Telegram Settings → Devices.
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession


def main():
    api_id_str = input("Enter TELEGRAM_API_ID: ").strip()
    api_hash = input("Enter TELEGRAM_API_HASH: ").strip()

    if not api_id_str.isdigit():
        print("❌ API_ID must be a number.")
        return

    api_id = int(api_id_str)

    async def run():
        async with TelegramClient(StringSession(), api_id, api_hash) as client:
            session_string = client.session.save()
            me = await client.get_me()

        print("\n" + "=" * 60)
        print(f"✅ Authenticated as: {me.first_name} (@{me.username})")
        print("=" * 60)
        print("\nAdd the following to your .env file:\n")
        print(f"TELEGRAM_API_ID={api_id}")
        print(f"TELEGRAM_API_HASH={api_hash}")
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        print("\n" + "=" * 60)
        print("⚠️  Keep this string SECRET — it gives full access to your Telegram account.")
        print("=" * 60 + "\n")

    asyncio.run(run())


if __name__ == "__main__":
    main()
