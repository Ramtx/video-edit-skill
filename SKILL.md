---
name: video-edit
description: >
  Load this skill whenever the user wants to edit a video file. This includes:
  cutting/removing segments, muting audio sections, adding captions or subtitles,
  adding word-level glowing captions (karaoke style), transcribing video with WhisperX,
  or any general video processing task. Also load when the user mentions ffmpeg,
  WhisperX, subtitles, captions, or trimming a video.
metadata: { "openclaw": { "emoji": "🎬", "requires": { "bins": ["ffmpeg", "whisperx", "python3"] } } }
disable-model-invocation: true
---

# Video Edit Skill

This skill covers video editing using **ffmpeg** and **WhisperX**, including cutting segments, muting sections, and burning word-level glowing captions into the video.

---

## Tools & What Was Found

### ffmpeg
- Already installed at `/usr/bin/ffmpeg` (version 6.1.1, Ubuntu)
- Use for all video cutting, muting, compositing, and subtitle burning
- Input/output format: `.MOV` (from iPhone), `.mp4`, etc.

### WhisperX
- Installed at `/home/palm/.local/bin/whisperx`
- Runs on CUDA (GPU), compute type defaults to `float16`
- Produces **word-level timestamps** automatically (alignment is built-in, no extra flag needed)
- `--word_timestamps True` is NOT a valid flag — word timing is always included
- Output goes to a directory via `--output_dir`, format via `--output_format json`

### moviepy
- Installed via `pip install moviepy --break-system-packages` (v2.2.1)
- Available for Python-based video compositing if needed

### Python / PIL
- `PIL` (Pillow) v10.2.0 available
- `numpy` v2.4.3 available

---

## Workflow: Cut + Mute + Caption

### Step 1 — Edit the video (cut segments, mute sections)

Use `ffmpeg` with `-filter_complex` using `trim`/`atrim` + `concat`.

**Key timestamps (in seconds):**
- `0:13` = 13s, `0:17` = 17s, `0:53` = 53s, `1:06` = 66s, `1:52` = 112s, `1:57` = 117s

**Template — remove two segments and mute one section:**

```bash
ffmpeg -i input.MOV -filter_complex \
"[0:v]trim=start=0:end=13,setpts=PTS-STARTPTS[v1]; \
[0:a]atrim=start=0:end=13,asetpts=PTS-STARTPTS[a1]; \
[0:v]trim=start=13:end=17,setpts=PTS-STARTPTS[v2]; \
[0:a]atrim=start=13:end=17,asetpts=PTS-STARTPTS,volume=0[a2]; \
[0:v]trim=start=17:end=53,setpts=PTS-STARTPTS[v3]; \
[0:a]atrim=start=17:end=53,asetpts=PTS-STARTPTS[a3]; \
[0:v]trim=start=66:end=112,setpts=PTS-STARTPTS[v4]; \
[0:a]atrim=start=66:end=112,asetpts=PTS-STARTPTS[a4]; \
[0:v]trim=start=117,setpts=PTS-STARTPTS[v5]; \
[0:a]atrim=start=117,asetpts=PTS-STARTPTS[a5]; \
[v1][a1][v2][a2][v3][a3][v4][a4][v5][a5]concat=n=5:v=1:a=1[outv][outa]" \
-map "[outv]" -map "[outa]" output.MOV -y
```

**Rules:**
- `trim`/`atrim` + `setpts=PTS-STARTPTS` / `asetpts=PTS-STARTPTS` to re-anchor timestamps after trimming
- `volume=0` on an `atrim` segment = mute that section
- `concat=n=<N>:v=1:a=1` — N is the number of segments

**To only mute (no cut):** use `volume=enable='between(t,13,17)':volume=0` in a simpler `-af` filter.

---

### Step 2 — Transcribe with WhisperX

```bash
mkdir -p /path/to/output_dir
whisperx video.MOV --model base --output_format json --output_dir /path/to/output_dir
```

- Output JSON: `output_dir/video.json`
- JSON structure: `{ "segments": [ { "words": [ { "word": "Go", "start": 0.271, "end": 0.431, "score": 0.878 }, ... ] } ] }`
- Some words may be missing `start`/`end` if alignment failed — always filter: `[w for w in seg['words'] if 'start' in w and 'end' in w]`
- Warning about `torchcodec` is harmless — WhisperX still works fine
- Detected language printed in logs — confirm it's correct before proceeding

---

### Step 3 — Generate ASS subtitles with glowing active word

Create an `.ass` subtitle file where each word has its own dialogue entry showing the full line, with the active word glowing (cyan + blur) and surrounding words dimmed.

**Python script pattern:**

```python
import json

with open('whisperx_out/video.json') as f:
    data = json.load(f)

def to_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

MAX_WORDS = 5  # words per caption line — keep short for phone screens
lines = []
for seg in data['segments']:
    words = [w for w in seg.get('words', []) if 'start' in w and 'end' in w]
    if not words:
        continue
    for i in range(0, len(words), MAX_WORDS):
        lines.append(words[i:i + MAX_WORDS])

ass_events = []
for line_words in lines:
    for i, active_word in enumerate(line_words):
        word_start = active_word['start']
        # Snap end to next word's start for seamless transitions
        word_end = line_words[i + 1]['start'] if i + 1 < len(line_words) else active_word['end']

        parts = []
        for j, w in enumerate(line_words):
            text = w['word'].strip()
            if j == i:
                # Active word: bright white, full opacity, white glow outline
                parts.append(
                    r'{\1c&HFFFFFF&\1a&H00&\3c&HFFFFFF&\3a&H00&\bord4\blur10\shad0}' +
                    text + r'{\r}'
                )
            else:
                # Inactive: white, semi-transparent
                parts.append(
                    r'{\1c&HFFFFFF&\1a&H88&\3a&HFF&\bord0\blur0\shad0}' +
                    text + r'{\r}'
                )

        ass_events.append(
            f"Dialogue: 0,{to_ass_time(word_start)},{to_ass_time(word_end)},"
            f"Default,,0,0,0,," + ' '.join(parts)
        )

ass_content = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
Collisions: Normal
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,2,0,2,30,30,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + '\n'.join(ass_events)

with open('captions.ass', 'w', encoding='utf-8') as f:
    f.write(ass_content)
```

**ASS color format:** `&HAABBGGRR&` — note it's BGR not RGB. Alpha: `00` = opaque, `FF` = transparent.

**Alignment 2** = bottom-center. `MarginV=80` = 80px from bottom edge. Good for portrait phone video.

**Font size 44** works well for 720×1280 portrait — readable but not oversized.

---

### Step 4 — Burn captions into video

```bash
ffmpeg -i video.MOV -vf "ass=captions.ass" -c:v libx264 -crf 18 -c:a aac -b:a 128k output_captioned.MOV -y
```

- `ass=` filter renders the ASS file directly onto the video frames
- `-crf 18` = high quality (lower = better, 18-23 is typical range)
- Processing speed: ~10x realtime on this machine

---

## Quick Reference

| Task | Command |
|------|---------|
| Cut segment out | `trim`/`atrim` + `concat` in `-filter_complex` |
| Mute a section | `atrim` + `volume=0` or `-af volume=enable='between(t,S,E)':volume=0` |
| Transcribe | `whisperx video.MOV --model base --output_format json --output_dir out/` |
| Burn ASS captions | `ffmpeg -i video.MOV -vf "ass=captions.ass" ... output.MOV` |

## Video Info (iPhone MOV)
- Resolution: 720×1280 (portrait)
- Video: h264 High, ~3510 kb/s, 29.98 fps
- Audio: AAC LC, 44100 Hz, stereo, ~126 kb/s
- Typical duration after editing: varies
