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
SILENT_FRAME = b'\x00' * (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS // 10)  # Dữ liệu im lặng cho 0.1 giây

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
    
    print(f"Đã lưu file ghi âm: {file_name} (kích thước: {len(data)} bytes)")

    # Gửi file ghi âm qua DM
    try:
        user = await bot.fetch_user(YOUR_USER_ID)
        if user:
            await user.send(f"Ghi âm từ kênh {channel_name} (phần {part_number})", file=discord.File(file_name))
            print(f"Đã gửi file ghi âm đến DM của bạn ({user.name})")
        else:
            print(f"Không tìm thấy người dùng với ID {YOUR_USER_ID}")
    except Exception as e:
        print(f"Lỗi khi gửi file qua DM: {e}. Tiếp tục ghi âm...")
    finally:
        # Xóa file sau khi gửi (hoặc nếu gửi thất bại)
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"Đã xóa file: {file_name}")

# Hàm ghi âm từ kênh thoại
async def record_audio(voice_client, channel_name):
    if not voice_client:
        print("Không có voice client để ghi âm")
        return

    print(f"Bắt đầu ghi âm từ kênh {channel_name}...")

    # Tạo file tạm để ghi dữ liệu PCM
    data = b""
    part_number = 1
    start_time = time.time()
    temp_file = f"{OUTPUT_DIR}/{channel_name}_temp_{start_time}.pcm"

    with open(temp_file, 'wb') as f:
        try:
            while voice_client.is_connected():
                # Lấy dữ liệu PCM từ voice client (nếu có)
                pcm_data = getattr(voice_client, 'audio_buffer', None)
                if pcm_data:
                    f.write(pcm_data)
                    data += pcm_data
                    print(f"Đã ghi âm {len(pcm_data)} bytes từ kênh {channel_name} (có âm thanh)")
                else:
                    # Nếu không có âm thanh, ghi dữ liệu im lặng
                    f.write(SILENT_FRAME)
                    data += SILENT_FRAME
                    print(f"Đã ghi âm {len(SILENT_FRAME)} bytes từ kênh {channel_name} (im lặng)")

                # Kiểm tra kích thước
                if len(data) >= MAX_FILE_SIZE:
                    await save_and_send_audio(channel_name, data, part_number)
                    data = b""
                    part_number += 1
                    await asyncio.sleep(5)  # Chờ 5 giây trước khi gửi file tiếp theo
                
                await asyncio.sleep(0.1)  # Ghi dữ liệu mỗi 0.1 giây để tạo file liên tục
        except Exception as e:
            print(f"Lỗi khi ghi âm: {e}")
        finally:
            # Xóa file tạm
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            # Lưu và gửi phần cuối nếu có dữ liệu
            print(f"Người dùng ngắt kết nối hoặc bot rời kênh, gửi file ghi âm còn lại (kích thước: {len(data)} bytes)...")
            await save_and_send_audio(channel_name, data, part_number)
            print("Đã dừng ghi âm từ kênh thoại")

# Hàm kiểm tra định kỳ người tham gia kênh thoại
async def check_voice_channels():
    print("Đang chạy hàm check_voice_channels...")
    await bot.wait_until_ready()
    print(f'Self-bot đã sẵn sàng với tên {bot.user}')
    
    # Kiểm tra xem bot có trong server không
    guild = bot.get_guild(SERVER_ID)
    if not guild:
        print(f"Bot không tìm thấy server với ID {SERVER_ID}. Đảm bảo tài khoản đã tham gia server!")
        return

    print(f"Bot đã tham gia server: {guild.name}")

    # Kiểm tra quyền của bot
    me = guild.get_member(bot.user.id)
    if not me:
        print("Bot không tìm thấy chính nó trong server. Đảm bảo tài khoản đã tham gia!")
        return

    permissions = me.guild_permissions
    if not permissions.connect or not permissions.speak:
        print("Bot không có quyền Connect hoặc Speak trong server. Vui lòng kiểm tra quyền!")
        return

    recently_disconnected = False  # Biến để theo dõi trạng thái vừa ngắt kết nối
    while not bot.is_closed():
        voice_client = discord.utils.get(bot.voice_clients, guild=guild)  # Gán voice_client ở đây
        voice_channels = guild.voice_channels
        print(f"Đang kiểm tra {len(voice_channels)} kênh voice trong server...")

        # Kiểm tra kênh hiện tại của bot (nếu đang ở trong kênh)
        if voice_client:
            current_channel = voice_client.channel
            members = current_channel.members
            human_members = [member for member in members if not member.bot and member.id != bot.user.id]
            print(f"Kênh hiện tại {current_channel.name} có {len(members)} thành viên: {[member.name for member in members]}")
            print(f"Số lượng người dùng thật trong kênh {current_channel.name}: {len(human_members)}")
            if len(human_members) == 0:
                # Nếu không còn người dùng thật trong kênh hiện tại, rời kênh
                await voice_client.disconnect()
                print(f"Bot đã rời kênh {current_channel.name} vì không còn người dùng thật trong kênh")
                voice_client = None
                recently_disconnected = True
                await asyncio.sleep(5)  # Chờ 5 giây trước khi kiểm tra kênh khác để tránh vòng lặp
            else:
                recently_disconnected = False

        # Kiểm tra tất cả kênh voice để tìm kênh có người dùng thật
        for channel in voice_channels:
            members = channel.members
            print(f"Kênh {channel.name} có {len(members)} thành viên: {[member.name for member in members]}")
            
            # Đếm số lượng người dùng thật (không phải bot)
            human_members = [member for member in members if not member.bot and member.id != bot.user.id]
            print(f"Số lượng người dùng thật trong kênh {channel.name}: {len(human_members)}")

            if human_members and bot.user not in members:  # Nếu có người dùng thật trong kênh và bot chưa tham gia
                print(f"Phát hiện người dùng thật trong kênh {channel.name}")
                # Kiểm tra xem bot đã ở trong kênh khác chưa
                if voice_client:
                    print(f"Bot đã ở trong kênh {voice_client.channel.name}, rời kênh để tham gia kênh mới...")
                    await voice_client.disconnect()
                    voice_client = None
                    await asyncio.sleep(1)  # Chờ 1 giây trước khi tham gia kênh mới
                
                # Tham gia kênh mới
                try:
                    voice_client = await channel.connect()
                    print(f"Bot đã tham gia kênh {channel.name}")
                    # Bắt đầu ghi âm
                    bot.loop.create_task(record_audio(voice_client, channel.name))
                    recently_disconnected = False
                except Exception as e:
                    print(f"Lỗi khi tham gia kênh {channel.name}: {e}")
                    voice_client = None  # Đặt lại voice_client nếu không tham gia được
                    continue  # Tiếp tục kiểm tra kênh khác
        
        # Nếu vừa rời kênh, chờ lâu hơn để tránh tham gia lại ngay
        if recently_disconnected:
            await asyncio.sleep(10)  # Chờ thêm 10 giây nếu vừa rời kênh
        else:
            await asyncio.sleep(5)  # Kiểm tra mỗi 5 giây nếu không vừa rời kênh

# Sự kiện khi bot kết nối Gateway
@bot.event
async def on_connect():
    print("Bot đã kết nối với Gateway!")
    # Chạy hàm kiểm tra kênh thoại
    bot.loop.create_task(check_voice_channels())

# Sự kiện khi bot sẵn sàng (dự phòng)
@bot.event
async def on_ready():
    print(f'Self-bot đã sẵn sàng (on_ready) với tên {bot.user}')

# Chạy bot
print("Đang chạy bot với token từ biến môi trường...")
bot.run(os.getenv('DISCORD_TOKEN'))
