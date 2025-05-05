FROM python:3.9-slim

# Cài FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Cài đặt các thư viện Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép code
COPY . .

# Chạy bot
CMD ["python", "discord_self_bot.py"]
