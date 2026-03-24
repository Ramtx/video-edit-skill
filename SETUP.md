# Video Edit Skill — Setup

Claude skill for editing videos: cutting, muting, slow-motion, normalization, reframing, and word-level glowing captions using ffmpeg + WhisperX.

## Files Overview

```
make_captions.py               — caption generation tool (put in ~/tools/)
video_edit_hook.sh             — approval hook for ffmpeg/whisperx write ops
video-edit/SKILL.md            — skill definition (put in ~/.claude/skills/video-edit/)
video-edit/references/
  ffmpeg-reference.md          — all ffmpeg commands
  captions-reference.md        — WhisperX + ASS caption generation
```

## Requirements

- `ffmpeg` — `sudo apt install ffmpeg`
- `jq` — `sudo apt install jq` (required by the hook script)
- `whisperx` — `pip install whisperx` (requires CUDA for GPU acceleration)
- `python3` — standard library only (no extra packages needed)

## Setup Steps

### 1. Install the caption tool

```bash
mkdir -p ~/tools
cp make_captions.py ~/tools/
chmod +x ~/tools/make_captions.py
```

### 2. Install the skill

```bash
mkdir -p ~/.claude/skills/video-edit/references
cp video-edit/SKILL.md ~/.claude/skills/video-edit/
cp video-edit/references/ffmpeg-reference.md ~/.claude/skills/video-edit/references/
cp video-edit/references/captions-reference.md ~/.claude/skills/video-edit/references/
```

### 3. Install the hook

```bash
mkdir -p ~/.claude/hooks
cp video_edit_hook.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/video_edit_hook.sh
```

Add to `~/.claude/settings.json` under `hooks.PreToolUse`:

```json
{
  "type": "command",
  "command": "/home/YOUR_USERNAME/.claude/hooks/video_edit_hook.sh"
}
```

> **Note:** Replace `/home/YOUR_USERNAME/` with your actual home directory path.

### 4. Restart Claude Code

Type `/video-edit` to load the skill.

## Usage

Drop a video file in the conversation. Claude will:
1. Ask 7 questions (trim, mute, normalize, reframe, speed, captions, filename)
2. Process step by step using `current.MOV` as the working file
3. Deliver the final output with captions burned in

## Quick Command Reference

```bash
# Scan (probe only — no output file written)
ffmpeg -i current.MOV -af silencedetect=noise=-30dB:d=1.5 -f null -    # silence gaps
ffmpeg -i current.MOV -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -f null -  # scene changes

# Edit (write to next.MOV, then rename — ffmpeg cannot write in-place)
ffmpeg -i current.MOV -filter_complex "..." next.MOV -y && mv next.MOV current.MOV  # cut/mute
ffmpeg -i current.MOV -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy next.MOV -y && mv next.MOV current.MOV  # normalize
ffmpeg -i current.MOV -vf "crop=..." next.MOV -y && mv next.MOV current.MOV        # reframe

# Captions (JSON output is named after the input basename: current.MOV → current.json)
whisperx current.MOV --model base --output_format json --output_dir /tmp/out
python3 ~/tools/make_captions.py --input /tmp/out/current.json --output captions.ass
ffmpeg -i current.MOV -vf "ass=captions.ass" output.MOV -y             # burn
```
