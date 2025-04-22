# Discord Music Bot

A Discord bot that plays music from YouTube in voice channels.

## Features

- Play music from YouTube
- Queue system for multiple songs
- Volume control
- Pause/resume functionality
- Song information display with progress bar

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your Discord token: `DISCORD_TOKEN=your_token_here`
4. Ensure FFmpeg is installed on your system
5. Run the bot: `python kaori.py`

## Commands

- `/play [query]`: Play a song or add it to the queue
- `/pause`: Pause the current song
- `/resume`: Resume playback
- `/skip`: Skip to the next song
- `/stop`: Stop playback and clear the queue
- `/volume [0-100]`: Adjust playback volume
- `/nowplaying`: Show information about the current song
- `/queue`: Display the current queue