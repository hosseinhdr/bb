"""
Telegram session userbot.

Flow (works ONLY in your Saved Messages — every other private chat is ignored):
  1. Logs into your account (phone + code -> session file).
  2. When a photo/video is SENT or FORWARDED into your Saved Messages, the bot
     replies asking for a caption.
  3. Your next text message becomes the caption.
  4. The bot re-uploads the media as a FRESH copy (no forward header, no
     original sender name) with that caption into your Saved Messages.

Run:  python bot.py
"""

import logging
import os
import sqlite3
import sys

from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
# Quiet Telethon's internal connection chatter so login prompts stay readable.
logging.getLogger("telethon").setLevel(logging.WARNING)
log = logging.getLogger("userbot")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")
# SESSION_PATH wins if set (may be an absolute path); otherwise fall back to the
# session *name*, which Telethon turns into "<name>.session" in the cwd.
SESSION = os.getenv("SESSION_PATH") or os.getenv("SESSION_NAME", "userbot")

if not API_ID or not API_HASH:
    raise SystemExit("Missing API_ID / API_HASH. Copy .env.example to .env and fill it in.")

# The path Telethon will actually open, so we can check it and report clearly.
_session_file = SESSION if SESSION.endswith(".session") else SESSION + ".session"
log.info("Using session file: %s", os.path.abspath(_session_file))

client = TelegramClient(SESSION, API_ID, API_HASH)

# Our own user id. "Saved Messages" is the private chat whose peer is yourself,
# i.e. chat_id == MY_ID. Set once at login; used to ignore every other chat.
MY_ID = None

# chat_id -> the pending media Message we are waiting to caption
pending = {}

# IDs of messages the bot itself produced, so it never reacts to its own output
self_sent = set()


def _is_media(message) -> bool:
    """True only for photos and videos (incl. video sent as a document)."""
    return bool(message.photo or message.video)


async def _remember(coro):
    """Await a send/reply coroutine and record its message id so we ignore it."""
    msg = await coro
    if msg is not None:
        self_sent.add(msg.id)
    return msg


@client.on(events.NewMessage(func=lambda e: e.is_private))
async def handler(event):
    # Only ever act inside Saved Messages (the chat with yourself). Ignore every
    # other private chat.
    if event.chat_id != MY_ID:
        return

    # Never react to messages we created ourselves.
    if event.message.id in self_sent:
        return

    chat_id = event.chat_id

    # 1) A photo/video arrived -> ask for a caption.
    if _is_media(event.message):
        pending[chat_id] = event.message
        await _remember(
            event.reply("📎 Send me a caption for this media (or /skip for none).")
        )
        return

    # 2) We are waiting for a caption in this chat.
    if chat_id in pending and event.message.text is not None:
        # Only use a stripped copy to detect commands. The caption we actually
        # send must be the RAW text with its original entities, otherwise custom
        # (animated) emoji, bold/italic, links, etc. are lost — e.g. a custom
        # emoji logo would fall back to its base emoji (❤️).
        command = event.message.raw_text.strip()

        if command.startswith("/cancel"):
            pending.pop(chat_id, None)
            await _remember(event.reply("❌ Cancelled."))
            return

        if command.startswith("/skip"):
            caption, entities = "", None
        else:
            # raw_text offsets line up with .entities (both UTF-16). Do NOT strip
            # this, or the entity offsets would no longer point at the right chars.
            caption = event.message.raw_text
            entities = event.message.entities

        media_msg = pending.pop(chat_id)

        # Re-upload the media as a fresh copy (strips forward header / sender name)
        # into Saved Messages ("me"), carrying the caption's formatting exactly.
        await _remember(
            client.send_file(
                "me",
                media_msg.media,
                caption=caption,
                formatting_entities=entities,
            )
        )
        await _remember(event.reply("✅ Saved to your Saved Messages."))
        log.info("Saved media from chat %s (caption: %r)", chat_id, caption)


async def login():
    """Explicit sign-in with clearly-flushed prompts (avoids silent input hangs)."""
    from getpass import getpass

    from telethon.errors import SessionPasswordNeededError

    try:
        await client.connect()
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            raise SystemExit(
                f"Session '{_session_file}' is locked — another bot.py/login.py is "
                "probably still running. Stop it first:\n"
                "    pkill -f bot.py"
            )
        raise

    if await client.is_user_authorized():
        return

    # No authorized session. Interactive login needs a real terminal (to type the
    # phone code) — inside Docker/systemd there is none, so fail loudly instead of
    # hanging on input() forever.
    if not sys.stdin.isatty():
        raise SystemExit(
            f"Not logged in and no interactive terminal is attached.\n"
            f"The session at SESSION_PATH ({_session_file}) is missing or not "
            f"authorized.\nLog in once on a machine with a terminal:\n"
            f"    python login.py\n"
            f"then make that .session file available at SESSION_PATH (mount it "
            f"into the container)."
        )

    phone = PHONE or input("Phone number (international format, e.g. +98...): ").strip()
    print(f"\n>>> Sending login code to {phone} …", flush=True)
    await client.send_code_request(phone)

    while True:
        code = input(">>> Enter the login code Telegram sent you: ").strip()
        try:
            await client.sign_in(phone=phone, code=code)
            break
        except SessionPasswordNeededError:
            pw = getpass(">>> Two-step password (input hidden): ")
            await client.sign_in(password=pw)
            break


async def main():
    global MY_ID
    await login()
    me = await client.get_me()
    MY_ID = me.id
    log.info(
        "Logged in as %s (id=%s). Listening in Saved Messages only…",
        me.first_name, me.id,
    )
    await client.run_until_disconnected()


if __name__ == "__main__":
    # `client` is created at module level, so it is bound to Telethon's own event
    # loop. Running main() on that same loop avoids the "Future attached to a
    # different loop" hang that asyncio.run() (a fresh loop) triggers here.
    client.loop.run_until_complete(main())
