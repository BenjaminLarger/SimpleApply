#!/bin/bash

# Script to play audio without overlapping
# Usage: ./play_audio.sh /path/to/audio.mp3

AUDIO_FILE="$1"

if [ -z "$AUDIO_FILE" ]; then
    echo "Usage: $0 <audio_file>"
    exit 1
fi

if [ ! -f "$AUDIO_FILE" ]; then
    echo "Audio file not found: $AUDIO_FILE"
    exit 1
fi

# Kill any existing audio players to prevent overlap
# Be more specific to avoid killing this script
pkill -f "^play " > /dev/null 2>&1  # Only kill processes starting with "play "
pkill -f "^ffplay " > /dev/null 2>&1
pkill -f "^aplay " > /dev/null 2>&1

# Small delay to ensure processes are killed
sleep 0.1

# Play the audio file
echo "Playing audio: $AUDIO_FILE"
play "$AUDIO_FILE" > /dev/null 2>&1 &