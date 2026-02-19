#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys

def mix_audio(voice_file, bg_music, output_file, volume=0.08):
    """
    Mix voice audio with background music using ffmpeg.
    """
    # Resolve relative paths to absolute paths
    voice_file = os.path.abspath(os.path.expanduser(voice_file))
    bg_music = os.path.abspath(os.path.expanduser(bg_music))
    output_file = os.path.abspath(os.path.expanduser(output_file))

    if not os.path.exists(voice_file):
        print(f"Error: Voice file {voice_file} not found.")
        return False
    if not os.path.exists(bg_music):
        print(f"Error: Background music {bg_music} not found.")
        return False

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Filter complex: 
    # [1:a]volume=0.08[bg]; mix the background music at low volume
    # [0:a][bg]amix=inputs=2:duration=first; mix with voice, duration matches voice
    cmd = [
        "ffmpeg", "-i", voice_file, "-i", bg_music,
        "-filter_complex", f"[1:a]volume={volume}[bg];[0:a][bg]amix=inputs=2:duration=first",
        "-y", output_file
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error mixing audio: {e.stderr.decode()}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mix voice with background music.")
    parser.add_argument("voice", help="Path to voice mp3 file")
    parser.add_argument("bg", help="Path to background music mp3 file")
    parser.add_argument("output", help="Path to output mixed mp3 file")
    parser.add_argument("--volume", type=float, default=0.08, help="Volume of background music (default 0.08)")

    args = parser.parse_args()
    if mix_audio(args.voice, args.bg, args.output, args.volume):
        print(f"Successfully created: {args.output}")
    else:
        sys.exit(1)
