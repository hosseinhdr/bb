# Telegram Caption Userbot

A Telegram **session bot** (userbot) that logs into your account. When a
photo/video is **sent or forwarded** into your **Saved Messages**, it asks you
for a caption, then re-uploads the media as a **fresh copy** (no forward header,
no original sender name) with that caption back into your Saved Messages. It
**only** acts in Saved Messages — every other private chat is ignored.

## How it works

1. Log into your account (phone number + login code → a `.session` file).
2. Send or forward a **photo/video** into your **Saved Messages**.
3. Bot replies: *"📎 Send me a caption for this media (or /skip for none)."*
4. Reply with your caption text (`/skip` = no caption, `/cancel` = abort).
5. Bot copies the media + caption into **Saved Messages** — clean, no sender name.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Get `API_ID` and `API_HASH` from https://my.telegram.org → *API development
tools*, and put your phone number in `.env`.

## Run

```bash
python bot.py
```

On first run you'll be asked for the login code Telegram sends you (and your
2FA password if enabled). After that the `.session` file keeps you logged in.

## Deploy with Docker

The container **cannot** do the interactive phone-code login, so log in **once
locally** to create the session, then ship that session file to the server.

1. Log in locally to produce `userbot.session`:

   ```bash
   python login.py
   ```

2. Put the session where the compose volume expects it:

   ```bash
   mkdir -p session && cp userbot.session session/
   ```

3. Make sure `.env` has `API_ID`, `API_HASH`, `PHONE`. The session path is
   supplied by the container via `SESSION_PATH=/data/userbot.session` (set in
   `docker-compose.yml` / the `Dockerfile`) — it points at the mounted
   `./session` volume, so you don't log in again.

4. Build & run:

   ```bash
   docker compose up -d --build
   docker compose logs -f          # should show "Listening in Saved Messages only…"
   ```

The `./session` directory is mounted read-write so Telethon can keep the session
fresh across restarts. `restart: unless-stopped` keeps the bot running.

## Notes

- This is a **userbot** — it runs as *your* account, not a BotFather bot.
  Automating a user account is against Telegram's ToS in some cases; use
  responsibly on an account you own.
- `.env` and `*.session` are git-ignored — never commit them.
