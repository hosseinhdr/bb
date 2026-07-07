"""
One-time login helper. Run this ONCE in a real terminal to authorize your
account and create the .session file. After it prints "LOGIN COMPLETE", run
`python bot.py` normally.

    python login.py
"""

import asyncio
import os
from getpass import getpass

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")
# Keep this in sync with bot.py: SESSION_PATH (if set) wins over SESSION_NAME,
# so login.py writes the session exactly where bot.py will later read it.
SESSION = os.getenv("SESSION_PATH") or os.getenv("SESSION_NAME", "userbot")


async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"\n✅ Already logged in as {me.first_name} (id={me.id}). Nothing to do.")
        await client.disconnect()
        return

    phone = PHONE or input("Phone (international format, e.g. +98...): ").strip()

    print(f"\n>>> Requesting a login code for {phone} …", flush=True)
    sent = await client.send_code_request(phone)
    print(">>> Code sent. Check your Telegram app (login code message).", flush=True)

    while True:
        code = input(">>> Enter the code (digits only): ").strip().replace(" ", "")
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
            break
        except PhoneCodeInvalidError:
            print("   ✗ Wrong code, try again.", flush=True)
        except PhoneCodeExpiredError:
            print("   ✗ Code expired. Requesting a new one…", flush=True)
            sent = await client.send_code_request(phone)
        except SessionPasswordNeededError:
            pw = getpass(">>> Two-step password (hidden): ")
            await client.sign_in(password=pw)
            break

    me = await client.get_me()
    print(f"\n✅ LOGIN COMPLETE — signed in as {me.first_name} (id={me.id}).")
    print("   Now run:  python3 bot.py")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
