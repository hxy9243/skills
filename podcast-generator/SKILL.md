---
name: podcast-generator
description: Generate high-quality audio podcasts or briefings with background music. Handles script drafting (Mandarin or English), TTS generation, and professional mixing with ambient background tracks. Use when creating "briefings", "audio updates", "family reports", or "podcasts".
---

# Podcast Generator 🎙️

This skill streamlines the creation of audio briefings and podcasts, ensuring clean narration and professional background music mixing.

## Workflow

1.  **Draft Script**:
    -   Write the script based on the requested topic.
    -   **Rule**: Do NOT include meta-instructions (like "Now use TTS tool") in the script.
    -   **Persona**: Embody "Friday" (🦞). Be sharp, calm, and concise.
    -   **Language**: Mandarin (default for family) or English (for Kevin).
    -   **Format**: Natural monologue only. No section headings or bracketed notes (e.g., "[Intro]").

2.  **Generate TTS**:
    -   Use the `tts` tool on the finalized script.
    -   Always generate as **MP3**.
    -   Path: Save the raw voice file to `~/.openclaw/media/temp_voice.mp3`.

3.  **Mix Background Music**:
    -   Select a track from `assets/music/` (default: `vladislav_zavorin-ambient-techno-405559.mp3` for ambient/tech vibes).
    -   Run the mixer script:
        ```bash
        python3 /home/kevin/.openclaw/skills/podcast-generator/scripts/mix_audio.py \
          ~/.openclaw/media/temp_voice.mp3 \
          /home/kevin/.openclaw/skills/podcast-generator/assets/music/<selected_track>.mp3 \
          ~/.openclaw/media/<filename>_briefing.mp3 \
          --volume 0.08
        ```

4.  **Deliver**:
    -   Send the final mixed file via Telegram using the `message` tool.
    -   Path for delivery: `/home/kevin/.openclaw/media/<filename>_briefing.mp3`.

## Audio Assets
Available in `assets/music/`:
- `vladislav_zavorin-ambient-techno-405559.mp3` (Ambient Techno - High quality)
- `tech_ambient_1.mp3`
- `tech_ambient_2.mp3`
- `musinova-orbits-90s-electronic-ambient-loopable-edit-477241.mp3`

## Constraints
- **Absolute Paths**: Always use absolute paths for ffmpeg and script execution.
- **Volume**: Keep background music at `0.08` to ensure voice clarity.
- **Durable Storage**: Save outputs in `~/.openclaw/media/`.
