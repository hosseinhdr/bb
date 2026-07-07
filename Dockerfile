FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the bot code goes in the image. The .session file is NOT baked in — the
# bot loads it at runtime from SESSION_PATH (see below), mounted as a volume.
COPY bot.py .

# The session the bot must use, taken from the environment. This default points
# at the mounted volume; override it with `-e SESSION_PATH=...` or in .env /
# docker-compose. The session file itself must exist at this path (mount it in).
ENV SESSION_PATH=/data/userbot.session

# Run only the bot.
CMD ["python", "-u", "bot.py"]
