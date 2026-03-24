# ffmpeg Reference

All commands use `current.MOV` as input/output per the pipeline rule. Replace timestamps (in seconds) with the user's values.

---

## Auto-scan (run before asking questions)

**Scene detection** — timestamps where visual content changes significantly:
```bash
ffmpeg -i current.MOV -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -f null - 2>&1 \
  | grep "pts_time" | awk -F'pts_time:' '{print $2}' | awk '{print $1}'
```

**Silence detection** — audio gaps below -30dB for more than 1.5s (dead air):
```bash
ffmpeg -i current.MOV -af silencedetect=noise=-30dB:d=1.5 -f null - 2>&1 | grep "silence_"
```

Present results to user: "I found scene changes at 0:12, 0:45 and silence gaps at 0:08–0:11, 1:22–1:25. Want to cut any of these?"

---

## Step 1 — Cut segments / mute sections

```bash
ffmpeg -i current.MOV -filter_complex \
"[0:v]trim=start=0:end=13,setpts=PTS-STARTPTS[v1]; \
[0:a]atrim=start=0:end=13,asetpts=PTS-STARTPTS[a1]; \
[0:v]trim=start=13:end=17,setpts=PTS-STARTPTS[v2]; \
[0:a]atrim=start=13:end=17,asetpts=PTS-STARTPTS,volume=0[a2]; \
[0:v]trim=start=17:end=53,setpts=PTS-STARTPTS[v3]; \
[0:a]atrim=start=17:end=53,asetpts=PTS-STARTPTS[a3]; \
[0:v]trim=start=66,setpts=PTS-STARTPTS[v4]; \
[0:a]atrim=start=66,asetpts=PTS-STARTPTS[a4]; \
[v1][a1][v2][a2][v3][a3][v4][a4]concat=n=4:v=1:a=1[outv][outa]" \
-map "[outv]" -map "[outa]" -c:v libx264 -crf 18 -c:a aac next.MOV -y && mv next.MOV current.MOV
```

**Rules:**
- Always use `setpts=PTS-STARTPTS` / `asetpts=PTS-STARTPTS` after every trim to re-anchor timestamps
- `volume=0` on an `atrim` segment = mute that section (keep the video, silence the audio)
- `concat=n=<N>:v=1:a=1` — N = number of segments
- To mute only (no cut): `-af volume=enable='between(t,S,E)':volume=0`

---

## Step 2 — Smooth slow-motion

Single-pass filter_complex — all segments share the same encode pipeline (no stream mismatch).

```bash
# Example: slow-mo from 0:30 to 0:35 at 0.5x speed
ffmpeg -i current.MOV -filter_complex \
"[0:v]trim=0:30,setpts=PTS-STARTPTS[v1]; \
[0:a]atrim=0:30,asetpts=PTS-STARTPTS[a1]; \
[0:v]trim=30:35,setpts=PTS-STARTPTS,minterpolate=fps=60:mi_mode=mci,setpts=2*PTS,drawtext=text='🐢 0.5x':fontsize=40:fontcolor=white:x=w-tw-30:y=30:shadowcolor=black:shadowx=2:shadowy=2[v2]; \
[0:a]atrim=30:35,asetpts=PTS-STARTPTS,atempo=0.5[a2]; \
[0:v]trim=35,setpts=PTS-STARTPTS[v3]; \
[0:a]atrim=35,asetpts=PTS-STARTPTS[a3]; \
[v1][a1][v2][a2][v3][a3]concat=n=3:v=1:a=1[outv][outa]" \
-map "[outv]" -map "[outa]" -c:v libx264 -crf 18 -c:a aac next.MOV -y && mv next.MOV current.MOV
```

**Key flags:**
- `minterpolate=fps=60` — generates frames to 60fps before slowing; result stays smooth 30fps after slowdown
- `mi_mode=mci` — motion compensated interpolation (best quality)
- `setpts=2*PTS` — 0.5x speed. Use `setpts=4*PTS` for 0.25x
- `atempo=0.5` — slows audio. Chain two for 0.25x: `atempo=0.5,atempo=0.5` (atempo range: 0.5–2.0)
- Emoji overlay is inline in `drawtext` — change `🐢 0.5x` to `⚡ 2x` for speed-up

**Speed reference:**

| Effect | `setpts` | `atempo` | Emoji label |
|--------|----------|----------|-------------|
| 0.5x slow | `setpts=2*PTS` | `atempo=0.5` | 🐢 0.5x |
| 0.25x slow | `setpts=4*PTS` | `atempo=0.5,atempo=0.5` | 🐢 0.25x |
| 2x fast | `setpts=0.5*PTS` | `atempo=2.0` | ⚡ 2x |
| 4x fast | `setpts=0.25*PTS` | `atempo=2.0,atempo=2.0` | ⚡ 4x |

---

## Step 3 — Audio normalization

```bash
ffmpeg -i current.MOV -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy next.MOV -y && mv next.MOV current.MOV
```

- `I=-16` — target loudness (LUFS), standard for online video
- `TP=-1.5` — true peak ceiling to prevent clipping
- `LRA=11` — loudness range (dynamic variation)
- `-c:v copy` — video untouched, audio only re-encoded

---

## Step 4 — Social reframing

```bash
# TikTok / Reels — 9:16 (iPhone MOV is already 9:16, no reframing needed)
ffmpeg -i current.MOV -vf "crop=ih*9/16:ih,scale=1080:1920" next.MOV -y && mv next.MOV current.MOV

# YouTube — 16:9
ffmpeg -i current.MOV -vf "crop=iw:iw*9/16,scale=1920:1080" next.MOV -y && mv next.MOV current.MOV

# Instagram — 1:1 (min dimension crop — works on both portrait and landscape)
ffmpeg -i current.MOV -vf "crop=min(iw\,ih):min(iw\,ih),scale=1080:1080" next.MOV -y && mv next.MOV current.MOV
```

| Platform | Aspect Ratio | Resolution |
|----------|-------------|------------|
| TikTok / Reels | 9:16 | 1080×1920 |
| YouTube | 16:9 | 1920×1080 |
| Instagram | 1:1 | 1080×1080 |

---

## Step 7 — Burn captions

*(Steps 5 and 6 — transcribe with WhisperX + generate captions .ass file — are in captions-reference.md)*

Check for existing file first:
```bash
[ -f output.MOV ] && echo "FILE EXISTS"
```

Burn captions only:
```bash
ffmpeg -i current.MOV -vf "ass=captions.ass" -c:v libx264 -crf 18 -c:a aac -b:a 128k output.MOV -y
```

Burn captions + reframe in one pass:
```bash
ffmpeg -i current.MOV -vf "crop=ih*9/16:ih,scale=1080:1920,ass=captions.ass" -c:v libx264 -crf 18 -c:a aac -b:a 128k output.MOV -y
```

- `-crf 18` — high quality (18–23 is typical; lower = better)
- Processing speed: ~10x realtime on this machine

---

## Video Info (iPhone MOV)

- Resolution: 720×1280 (portrait, 9:16)
- Video: h264 High, ~3510 kb/s, 29.98 fps
- Audio: AAC LC, 44100 Hz, stereo, ~126 kb/s
