FROM python:3.10-slim

# Cài FFmpeg và libsodium (cần cho PyNaCl)
RUN apt-get update && apt-get install -y ffmpeg libsodium-dev

# Nâng cấp pip
RUN pip install --upgrade pip

# Cài đặt các thư viện Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép code
COPY . .

# Chạy bot
CMD ["python", "discord_self_bot.py"]
