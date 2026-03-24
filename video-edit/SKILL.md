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

**Phase 1 — Gather all answers before touching the video.**

Run scene and silence detection first (see ffmpeg-reference.md), then ask each question using `AskUserQuestion` one at a time. Wait for every answer before starting any processing.

**Q1 — Trim or remove sections?**
Options: `Manual`, `Suggest`, `No`

If Suggest → show the suggested timestamps from the scan and ask:
**These are the sections I'd suggest cutting: [timestamps]. Approve or edit?**
Options: `Approve`, `Edit` *(user types custom timestamps)*

If Manual → ask: **Which timestamps do you want to remove?** *(free text)*

**Q2 — Mute any part of the video?**
Options: `Yes`, `No`

**Q3 — Audio sounds uneven? Want me to normalize it?**
Options: `Yes`, `No`

**Q4 — Social reframing?**
Options: `Keep original`, `Custom` *(user types the platform or dimensions)*

**Q5 — Speed up or slow down any part?**
Options: `Yes`, `No`

If yes on Q5, follow up immediately (still in Phase 1):
**How do you want to pick the sections?**
Options: `Auto`, `Manual`

**Q6 — Captions?**
Options: `Default`, `Manual`, `No captions`

**Q7 — Output filename?**
*(free text — no options)*

Once all answers are collected, check if the output file already exists — if it does, warn the user before starting.
Options: `Overwrite`, `Cancel`

---

**Phase 2 — Process the video step by step** using the answers from Phase 1. Do not stop between steps to ask for approval — execute each step in order and report progress as you go.

---

## Step Order

1. Cut / mute sections (filter_complex)
2. Slow-motion (filter_complex)
3. Audio normalization (loudnorm)
4. Social reframing (crop + scale)
5. Transcribe (whisperx)
6. Generate captions (make_captions.py)
7. Burn captions into video (ass= filter) → write final output file
