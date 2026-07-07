FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py login.py ./

# The Telethon session file lives on a mounted volume (see docker-compose.yml).
# SESSION_PATH points bot.py at it so the session persists across restarts.
ENV SESSION_PATH=/data/userbot.session

CMD ["python", "-u", "bot.py"]
