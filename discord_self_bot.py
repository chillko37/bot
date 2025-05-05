import discord
from discord.ext import commands
import asyncio
import os
from datetime import datetime
import time

# Thêm log ngay từ đầu
print("Bắt đầu khởi động bot...")

# Khởi tạo bot
bot = commands.Bot(command_prefix='!', self_bot=True)

# Cấu hình ghi âm
SAMPLE_RATE = 48000  # Tần số mẫu của Discord
SAMPLE_WIDTH = 2  # 16-bit audio (2 bytes per sample)
CHANNELS = 2  # Stereo
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB in bytes
OUTPUT_DIR = "recordings"

# ID của server (theo yêu cầu của bạn)
SERVER_ID = 1191611855433646140

# ID của bạn để gửi file ghi âm qua DM
YOUR_USER_ID = 1080848303580782592

# Tạo thư mục lưu file ghi âm nếu chưa có
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Hàm lưu và gửi file ghi âm
async def save_and_send_audio(channel_name, data, part_number):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{OUTPUT_DIR}/{channel_name}_{timestamp}_part{part_number}.wav"
    
    with open(file_name, 'wb') as f:
        # Tạo header WAV
        f.write(b'RIFF')
        f.write((36 + len(data)).to_bytes(4, 'little'))  # File size
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write((16).to_bytes(4, 'little'))  # Subchunk size
        f.write((1).to_bytes(2, 'little'))  # Audio format (PCM)
        f.write((CHANNELS).to_bytes(2, 'little'))  # Channels
        f.write((SAMPLE_RATE).to_bytes(4, 'little'))  # Sample rate
        f.write((SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH).to_bytes(4, 'little'))  # Byte rate
        f.write((CHANNELS * SAMPLE_WIDTH).to_bytes(2, 'little'))  # Block align
        f.write((SAMPLE_WIDTH * 8).to_bytes(2, 'little'))  # Bits per sample
        f.write(b'data')
        f.write((len(data)).to_bytes(4, 'little'))  # Data size
        f.write(data)  # Audio data
    
    print(f"Đã lưu file ghi âm: {file_name}")

    # Gửi file ghi âm qua DM
    user = await bot.fetch_user(YOUR_USER_ID)
    if user:
        try:
            await user.send(f"Ghi âm từ kênh {channel_name} (phần {part_number})", file=discord.File(file_name))
            print(f"Đã gửi file ghi âm đến DM của bạn ({user.name})")
            # Xóa file sau khi gửi để bảo mật
            os.remove(file_name)
            print(f"Đã xóa file: {file_name}")
        except Exception as e:
            print(f"Lỗi khi gửi file qua DM: {e}")
    else:
        print(f"Không tìm thấy người dùng với ID {YOUR_USER_ID}")

# Hàm ghi âm từ kênh thoại
async def record_audio(voice_client, channel_name):
    if not voice_client:
        print("Không có voice client để ghi âm")
        return

    # Tạo sink để nhận luồng âm thanh từ kênh thoại
    try:
        sink = discord.sinks.WaveSink()
        voice_client.start_recording(sink, None)
    except AttributeError:
        print("WaveSink không được hỗ trợ trong phiên bản này của discord.py-self.")
        return
    
    data = b""
    part_number = 1
    start_time = time.time()
    print(f"Đang ghi âm từ kênh {channel_name}...")

    try:
        while voice_client.is_connected():
            await asyncio.sleep(1)  # Kiểm tra mỗi giây
            # Lấy dữ liệu từ sink
            if hasattr(sink, 'audio_data') and sink.audio_data:
                new_data = sink.get_data()
                data += new_data
                
                # Kiểm tra kích thước
                if len(data) >= MAX_FILE_SIZE:
                    await save_and_send_audio(channel_name, data, part_number)
                    data = b""
                    part_number += 1
                    await asyncio.sleep(5)  # Chờ 5 giây trước khi gửi file tiếp theo để tránh bị chặn
    except Exception as e:
        print(f"Lỗi khi ghi âm: {e}")
    finally:
        voice_client.stop_recording()
        # Lưu và gửi phần cuối nếu còn dữ liệu
        if data:
            await save_and_send_audio(channel_name, data, part_number)
        print("Đã dừng ghi âm từ kênh thoại")

# Hàm kiểm tra định kỳ người tham gia kênh thoại
async def check_voice_channels():
    await bot.wait_until_ready()
    print(f'Self-bot đã sẵn sàng với tên {bot.user}')
    
    # Kiểm tra xem bot có trong server không
    guild = bot.get_guild(SERVER_ID)
    if not guild:
        print(f"Bot không tìm thấy server với ID {SERVER_ID}. Đảm bảo tài khoản đã tham gia server!")
        return

    print(f"Bot đã tham gia server: {guild.name}")

    while not bot.is_closed():
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)  # Gán voice_client ở đây
        voice_channels = guild.voice_channels
        for channel in voice_channels:
            members = channel.members
            if members and bot.user not in members:  # Nếu có người trong kênh và bot chưa tham gia
                print(f"Phát hiện người dùng trong kênh {channel.name}")
                # Kiểm tra xem bot đã ở trong kênh thoại nào chưa
                if voice_client:
                    print(f"Bot đã ở trong kênh {voice_client.channel.name}, bỏ qua...")
                    continue
                
                # Tham gia kênh thoại
                try:
                    voice_client = await channel.connect()
                    print(f"Bot đã tham gia kênh {channel.name}")
                    # Bắt đầu ghi âm
                    bot.loop.create_task(record_audio(voice_client, channel.name))
                except Exception as e:
                    print(f"Lỗi khi tham gia kênh {channel.name}: {e}")
            elif voice_client and voice_client.channel == channel and len(channel.members) == 1:
                # Nếu chỉ còn bot trong kênh, rời kênh
                await voice_client.disconnect()
                print(f"Bot đã rời kênh {channel.name} vì không còn ai trong kênh")
                voice_client = None  # Đặt lại voice_client sau khi rời
        
        await asyncio.sleep(10)  # Kiểm tra mỗi 10 giây

# Sự kiện khi bot sẵn sàng (dự phòng)
@bot.event
async def on_ready():
    print(f'Self-bot đã sẵn sàng (on_ready) với tên {bot.user}')
    # Chạy hàm kiểm tra kênh thoại
    bot.loop.create_task(check_voice_channels())

# Chạy bot
print("Đang chạy bot với token từ biến môi trường...")
bot.run(os.getenv('DISCORD_TOKEN'))
