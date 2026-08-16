#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys

def duration_seconds(audio_file):
    """Return an audio file's duration as seconds using ffprobe."""
    ffprobe = os.environ.get("FFPROBE_BIN", "ffprobe")
    result = subprocess.run(
        [
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_file,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def mix_audio(voice_file, bg_music, output_file, volume=0.08, outro_seconds=5):
    """
    Mix voice audio with background music using ffmpeg.
    """
    voice_file = os.path.abspath(os.path.expanduser(voice_file))
    bg_music = os.path.abspath(os.path.expanduser(bg_music))
    output_file = os.path.abspath(os.path.expanduser(output_file))

    if not os.path.exists(voice_file):
        print(f"Error: Voice file {voice_file} not found.")
        return False
    if not os.path.exists(bg_music):
        print(f"Error: Background music {bg_music} not found.")
        return False

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    try:
        voice_duration = duration_seconds(voice_file)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"Error reading voice duration: {e}")
        return False

    if outro_seconds < 0:
        print("Error: Outro duration cannot be negative.")
        return False

    total_duration = voice_duration + outro_seconds
    ffmpeg = os.environ.get("FFMPEG_BIN", "ffmpeg")
    bg_filter = f"[1:a]volume={volume},atrim=duration={total_duration}"
    if outro_seconds:
        bg_filter += f",afade=t=out:st={voice_duration}:d={outro_seconds}"
    bg_filter += "[bg]"

    cmd = [
        ffmpeg, "-i", voice_file, "-stream_loop", "-1", "-i", bg_music,
        "-filter_complex", f"{bg_filter};[0:a][bg]amix=inputs=2:duration=longest:dropout_transition=0",
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
    parser.add_argument(
        "--outro-seconds", type=float, default=5,
        help="Music-only fade-out duration after narration ends (default 5)",
    )

    args = parser.parse_args()
    if mix_audio(args.voice, args.bg, args.output, args.volume, args.outro_seconds):
        print(f"Successfully created: {args.output}")
    else:
        sys.exit(1)
