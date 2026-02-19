---
name: podcast-generator
description: Generate high-quality audio podcasts or briefings with background music. Handles script drafting, TTS generation, and mixing with ambient tracks. Use for briefings, podcasts, or audio reports.
---

# Podcast Generator 🎙️

This skill streamlines the creation of audio briefings and podcasts, ensuring clean narration and professional background music mixing.

## Workflow

1.  **Draft Script**:
    -   Write the script based on the requested topic.
    -   **Rule**: No meta-instructions or bracketed notes (e.g., "[Intro]") in the final script.
    -   **Persona**: Friday (🦞). Sharp, calm, concise.
    -   **Format**: Natural monologue.

2.  **Generate TTS**:
    -   Use the `tts` tool. Always generate as **MP3**.
    -   Save raw voice to: `~/.openclaw/media/temp_voice.mp3`.

3.  **Mix Background Music**:
    -   Select a track from `assets/music/` or find/download CC-licensed ambient techno if a specific vibe is requested.
    -   Run the mixer script using paths relative to the skill or user home:
        ```bash
        python3 ./scripts/mix_audio.py \
          ~/.openclaw/media/temp_voice.mp3 \
          ./assets/music/vladislav_zavorin-ambient-techno-405559.mp3 \
          ~/.openclaw/media/output_briefing.mp3 \
          --volume 0.08
        ```

4.  **Deliver**:
    -   Send the final mixed file via Telegram.
    -   Standard delivery path: `~/.openclaw/media/`.

## Open Source Music Sources
If specific background tracks are needed, search for and download Creative Commons (CC-BY / CC0) licensed music from:
- **Free Music Archive (FMA)**
- **Pixabay Music** (Filtered for "Ambient Techno")
- **Wikimedia Commons**
- **Incompetech** (Kevin MacLeod)

## Constraints
- **Relative Paths**: Use relative paths where possible or `~` expansion to avoid hardcoded environment strings.
- **Volume**: Keep background music at `0.08` for voice clarity.
- **Cleanup**: Temp files should be overwritten or cleaned up to save space.
