import discord
from discord.ext import commands
import asyncio
import os
from datetime import datetime
import time

# Khởi tạo self-bot với prefix và intents
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents, self_bot=True)

# Cấu hình ghi âm
SAMPLE_RATE = 48000  # Tần số mẫu của Discord
SAMPLE_WIDTH = 2  # 16-bit audio (2 bytes per sample)
CHANNELS = 2  # Stereo
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB in bytes
OUTPUT_DIR = "recordings"

# ID của server (từ link https://discord.gg/ahex)
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
    sink = discord.sinks.WaveSink()
    voice_client.start_recording(sink, None)
    
    data = b""
    part_number = 1
    start_time = time.time()
    print(f"Đang ghi âm từ kênh {channel_name}...")

    try:
        while voice_client.is_connected():
            await asyncio.sleep(1)  # Kiểm tra mỗi giây
            # Lấy dữ liệu từ sink
            if sink.audio_data:
                new_data = sink.get_data()
                data += new_data
                
                # Kiểm tra kích thước
                if len(data) >= MAX_FILE_SIZE:
                    await save_and_send_audio(channel_name, data, part_number)
                    data = b""
                    part_number += 1
    except Exception as e:
        print(f"Lỗi khi ghi âm: {e}")
    finally:
        voice_client.stop_recording()
        # Lưu và gửi phần cuối nếu còn dữ liệu
        if data:
            await save_and_send_audio(channel_name, data, part_number)
        print("Đã dừng ghi âm từ kênh thoại")

# Sự kiện khi bot sẵn sàng
@bot.event
async def on_ready():
    print(f'Self-bot đã sẵn sàng với tên {bot.user}')

# Sự kiện khi có người tham gia hoặc rời kênh thoại
@bot.event
async def on_voice_state_update(member, before, after):
    # Chỉ xử lý trong server cụ thể
    if member.guild.id != SERVER_ID:
        return

    # Nếu bot là người thay đổi trạng thái (để tránh vòng lặp)
    if member == bot.user:
        return

    # Nếu có người tham gia kênh thoại
    if after.channel and not before.channel:
        print(f"{member.name} đã tham gia kênh {after.channel.name}")
        # Kiểm tra xem bot đã ở trong kênh thoại nào chưa
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
        if voice_client:
            print(f"Bot đã ở trong kênh {voice_client.channel.name}, bỏ qua...")
            return
        
        # Tham gia kênh thoại
        try:
            voice_client = await after.channel.connect()
            print(f"Bot đã tham gia kênh {after.channel.name}")
            # Bắt đầu ghi âm từ kênh thoại
            asyncio.create_task(record_audio(voice_client, after.channel.name))
        except Exception as e:
            print(f"Lỗi khi tham gia kênh {after.channel.name}: {e}")

    # Nếu người cuối cùng rời kênh, bot cũng rời
    if before.channel and not after.channel:
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
        if voice_client and voice_client.channel == before.channel:
            # Kiểm tra xem còn ai trong kênh không
            if len(before.channel.members) == 1:  # Chỉ còn bot
                await voice_client.disconnect()
                print(f"Bot đã rời kênh {before.channel.name} vì không còn ai trong kênh")

# Chạy bot với user token (lấy từ biến môi trường trên Railway)
bot.run(os.getenv('DISCORD_TOKEN'))
