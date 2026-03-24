---
name: video-edit
description: >
  Load this skill whenever the user wants to edit a video file. This includes:
  cutting/removing segments, muting audio sections, adding captions or subtitles,
  adding word-level highlighted captions (karaoke style), transcribing video with WhisperX,
  or any general video processing task. Also load when the user mentions ffmpeg,
  WhisperX, subtitles, captions, or trimming a video.
  Tool location: python3 ~/tools/make_captions.py
disable-model-invocation: true
---

# Video Edit Skill

Video editing using **ffmpeg** and **WhisperX** — cutting, muting, slow-motion, normalization, reframing, and word-level highlighted captions.

## Tools

| Tool | Location |
|------|----------|
| ffmpeg | `ffmpeg` (system PATH) |
| whisperx | `whisperx` (system PATH or `~/.local/bin/whisperx`) |
| make_captions.py | `~/tools/make_captions.py` |

See `references/ffmpeg-reference.md` for all ffmpeg commands.
See `references/captions-reference.md` for WhisperX + ASS caption generation.

---

## Pipeline Rule

Start every job by copying the input: `cp input.MOV current.MOV`

**ffmpeg cannot write to the same file it reads.** Each step writes to `next.MOV`, then renames it:
```bash
ffmpeg -i current.MOV ... next.MOV -y && mv next.MOV current.MOV
```
The final caption burn writes directly to the user's chosen output filename instead of `current.MOV`.

---

## Workflow — Start Here

When the user provides a video, **first run scene and silence detection automatically** (see ffmpeg-reference.md), then ask all questions in **one single message**:

> 1. **Trim or remove sections?** — Manual or Suggest *(suggest sections, you approve or edit them)*
> 2. **Mute any part?** Yes or no.
> 3. **Audio normalization?** *(Evens out the volume across the whole video)* Yes or no?
> 4. **Social reframing?** Keep original or write which platform.
> 5. **Do you want to speed up or slow down any part of the video?** If yes, a follow-up question will appear. Type "no" to skip.
> 6. **Captions** — Default *(spoken word yellow, rest white, bottom position)* or Manual *(choose highlight color, text color, and position)*
> 7. **Output filename?**

If user says yes on Q5, ask:
> **How do you want to pick the sections?**
> - **Auto** *(I'll scan the video for silent gaps and pauses and suggest those as sections to speed up)*
> - **Manual**

Before writing any output file, **check if it already exists** — if it does, warn the user and ask if they want to overwrite.

---

## Step Order

1. Cut / mute sections (filter_complex)
2. Slow-motion (filter_complex)
3. Audio normalization (loudnorm)
4. Social reframing (crop + scale)
5. Transcribe (whisperx)
6. Generate captions (make_captions.py)
7. Burn captions into video (ass= filter) → write final output file
