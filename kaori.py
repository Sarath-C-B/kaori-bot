import os
import asyncio
import discord
import yt_dlp
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from collections import deque
import datetime
import time

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store song information and player state
class GuildMusicState:
    def __init__(self):
        self.queue = deque()
        self.current_song = None
        self.volume = 0.5  # Default volume (50%)
        self.start_time = None

# Dictionary to store music state for each guild
GUILD_MUSIC_STATES = {}

@bot.event
async def on_ready():
    print("nyahello~~~")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="greet", description="Sends a greeting to the user")
async def greet(interaction: discord.Interaction):
    username = interaction.user.mention
    await interaction.response.send_message(f"Nyahello, {username}")

async def search_ytdlp_async(query, ydl_opts):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))
        except Exception as e:
            print(f"Error in YouTube search (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # Wait longer between each retry
                await asyncio.sleep(2 * (attempt + 1))
            else:
                print("All search attempts failed")
                return None

def _extract(query, ydl_opts):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(query, download=False)
    except yt_dlp.utils.DownloadError as e:
        print(f"Download error: {e}")
        return None
    except Exception as e:
        print(f"Extraction error: {e}")
        return None

@bot.tree.command(name="skip", description="Skips the current playing song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipped the current song.")
    else:
        await interaction.response.send_message("Not playing anything to skip.")

@bot.tree.command(name="pause", description="Pause the currently playing song.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if something is actually playing
    if not voice_client.is_playing():
        return await interaction.response.send_message("Nothing is currently playing.")
    
    # Pause the track
    voice_client.pause()
    await interaction.response.send_message("Playback paused!")

@bot.tree.command(name="resume", description="Resume the currently paused song.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if voice_client is None:
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if it's actually paused
    if not voice_client.is_paused():
        return await interaction.response.send_message("I'm not paused right now.")
    
    # Resume playback
    voice_client.resume()
    await interaction.response.send_message("Playback resumed!")

@bot.tree.command(name="stop", description="Stop playback and clear the queue.")
async def stop(interaction: discord.Interaction):
    # Immediately acknowledge the interaction to prevent timeout
    await interaction.response.defer()

    voice_client = interaction.guild.voice_client

    # Check if the bot is in a voice channel
    if not voice_client or not voice_client.is_connected():
        return await interaction.followup.send("I'm not connected to any voice channel.")

    # Clear the guild's queue
    guild_id_str = str(interaction.guild_id)
    if guild_id_str in GUILD_MUSIC_STATES:
        GUILD_MUSIC_STATES[guild_id_str].queue.clear()
        GUILD_MUSIC_STATES[guild_id_str].current_song = None

    # If something is playing or paused, stop it
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    # Disconnect from the channel
    await voice_client.disconnect()

    await interaction.followup.send("Stopped playback and disconnected!")

@bot.tree.command(name="volume", description="Change the playback volume (0-100)")
@app_commands.describe(volume="Volume level (0-100)")
async def volume(interaction: discord.Interaction, volume: int):
    if volume < 0 or volume > 100:
        return await interaction.response.send_message("Volume must be between 0 and 100.")
    
    voice_client = interaction.guild.voice_client
    guild_id = str(interaction.guild_id)
    
    if not voice_client:
        return await interaction.response.send_message("I'm not currently playing anything.")
    
    # Ensure guild state exists
    if guild_id not in GUILD_MUSIC_STATES:
        GUILD_MUSIC_STATES[guild_id] = GuildMusicState()
    
    # Set volume (0.0 to 1.0)
    new_volume = volume / 100
    GUILD_MUSIC_STATES[guild_id].volume = new_volume
    
    if voice_client.source:
        voice_client.source.volume = new_volume
    
    await interaction.response.send_message(f"Volume set to {volume}%")

@bot.tree.command(name="nowplaying", description="Show information about the currently playing song")
async def nowplaying(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    voice_client = interaction.guild.voice_client
    
    if not voice_client or not voice_client.is_playing():
        return await interaction.response.send_message("Nothing is currently playing.")
    
    # Ensure guild state exists
    if guild_id not in GUILD_MUSIC_STATES:
        return await interaction.response.send_message("No song information available.")
    
    state = GUILD_MUSIC_STATES[guild_id]
    if not state.current_song:
        return await interaction.response.send_message("No song information available.")
    
    song = state.current_song
    
    # Calculate elapsed time
    elapsed = "Unknown"
    duration = "Unknown"
    progress_bar = ""
    
    if state.start_time and song.get('duration'):
        elapsed_seconds = int(time.time() - state.start_time)
        total_seconds = song.get('duration')
        
        # Format as MM:SS
        elapsed = str(datetime.timedelta(seconds=elapsed_seconds)).split('.')[0].removeprefix('0:')
        duration = str(datetime.timedelta(seconds=total_seconds)).split('.')[0].removeprefix('0:')
        
        # Create progress bar
        bar_length = 20
        filled_length = int(bar_length * elapsed_seconds / total_seconds)
        progress_bar = "▓" * filled_length + "░" * (bar_length - filled_length)
        progress_percent = int(100 * elapsed_seconds / total_seconds)
        
        progress_display = f"\n{elapsed} / {duration} [{progress_bar}] {progress_percent}%"
    
    # Create embed with song information
    embed = discord.Embed(title="Now Playing", color=discord.Color.blue())
    embed.add_field(name="Title", value=song.get('title', 'Unknown'), inline=False)
    
    if song.get('uploader'):
        embed.add_field(name="Channel", value=song.get('uploader', 'Unknown'), inline=True)
    
    if song.get('view_count'):
        embed.add_field(name="Views", value=f"{song.get('view_count', 0):,}", inline=True)
        
    if elapsed != "Unknown" and duration != "Unknown":
        embed.add_field(name="Progress", value=progress_display, inline=False)
    
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song.get('thumbnail'))
        
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="queue", description="Show the current song queue")
async def queue(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    
    if guild_id not in GUILD_MUSIC_STATES or len(GUILD_MUSIC_STATES[guild_id].queue) == 0:
        return await interaction.response.send_message("The queue is empty!")
    
    queue_list = "\n".join([f"{i+1}. {song.get('title', 'Unknown')}" for i, song in enumerate(GUILD_MUSIC_STATES[guild_id].queue)])
    
    await interaction.response.send_message(f"**Current Queue:**\n{queue_list}")

@bot.tree.command(name="play", description="Play a song or add it to the queue.")
@app_commands.describe(song_query="Search query")
async def play(interaction: discord.Interaction, song_query: str):
    await interaction.response.defer()
    
    # Check if user is in a voice channel
    if not interaction.user.voice:
        await interaction.followup.send("You must be in a voice channel to use this command.")
        return
    
    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client
    guild_id = str(interaction.guild_id)
    
    # Ensure guild state exists
    if guild_id not in GUILD_MUSIC_STATES:
        GUILD_MUSIC_STATES[guild_id] = GuildMusicState()
    
    # Connect to voice channel if not already connected
    if voice_client is None:
        try:
            voice_client = await voice_channel.connect()
        except discord.errors.ClientException as e:
            await interaction.followup.send(f"Failed to connect to voice channel: {e}")
            return
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)

    # Modify your ydl_options in the play command
    ydl_options = {
        "format": "bestaudio/best",  # Use the best available audio quality
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
        "quiet": True,
        "extract_flat": False,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",  # Discord works best with opus
            "preferredquality": "192",  # Higher quality (up to 192 is reasonable)
        }],
    }

    query = "ytsearch1: " + song_query
    results = await search_ytdlp_async(query, ydl_options)
    
    if not results or not results.get("entries"):
        await interaction.followup.send("No results found. Try a different search.")
        return

    tracks = results.get("entries", [])
    first_track = tracks[0]
    
    GUILD_MUSIC_STATES[guild_id].queue.append(first_track)
    
    title = first_track.get("title", "Untitled")

    if voice_client.is_playing() or voice_client.is_paused():
        await interaction.followup.send(f"Added to queue: **{title}**")
    else:
        await interaction.followup.send(f"Now playing: **{title}**")
        await play_next_song(voice_client, guild_id, interaction.channel)

async def play_next_song(voice_client, guild_id, channel):
    state = GUILD_MUSIC_STATES.get(guild_id)
    
    if not state or not state.queue:
        # No more songs in the queue
        await voice_client.disconnect()
        return
    
    # Get the next song from the queue
    song = state.queue.popleft()
    audio_url = song.get("url")
    title = song.get("title", "Untitled")
    
    if not audio_url:
        await channel.send(f"Could not play {title}: Missing URL")
        await play_next_song(voice_client, guild_id, channel)
        return
    
    # Store current song info and start time
    state.current_song = song
    state.start_time = time.time()
    
    # Create FFmpeg options
    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn -c:a libopus -b:a 192k -ar 48000",  # Higher bitrate and proper sample rate
    }
    
    # Try to find FFmpeg in PATH first
    try:
        source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)
    except Exception:
        # Fall back to hardcoded path as a last resort
        try:
            source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")
        except Exception as e:
            await channel.send(f"Error playing {title}: FFmpeg not found. Please install FFmpeg.")
            print(f"FFmpeg error: {e}")
            await play_next_song(voice_client, guild_id, channel)
            return
    
    # Set the volume
    source.volume = state.volume
    
    def after_play(error):
        if error:
            print(f"Error playing {title}: {error}")
            asyncio.run_coroutine_threadsafe(channel.send(f"Error playing {title}"), bot.loop)
        # Play next song regardless of error
        asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

    voice_client.play(source, after=after_play)
    
    # Create a more detailed message for now playing
    embed = discord.Embed(title="Now Playing", color=discord.Color.green())
    embed.add_field(name="Title", value=title, inline=False)
    
    if song.get('uploader'):
        embed.add_field(name="Channel", value=song.get('uploader', 'Unknown'), inline=True)
    
    if song.get('duration'):
        duration = str(datetime.timedelta(seconds=song.get('duration'))).split('.')[0].removeprefix('0:')
        embed.add_field(name="Duration", value=duration, inline=True)
    
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song.get('thumbnail'))
    
    await channel.send(embed=embed)

# Run the bot
bot.run(TOKEN)