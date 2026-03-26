# ffmpeg Reference

All commands use `current.MOV` as input/output per the pipeline rule. Replace timestamps (in seconds) with the user's values.

---

## Job Start — Run These Once Before Any Step

```bash
# GPU encoder — runtime test, not just compile-time check
ffmpeg -f lavfi -i nullsrc=s=64x64 -frames:v 1 -c:v h264_nvenc -f null - 2>/dev/null \
  && VFLAGS="-c:v h264_nvenc -preset p4 -cq 18" \
  || VFLAGS="-c:v libx264 -crf 18"

# Intermediate audio codec — PCM avoids AAC encoder-delay artifacts between segment joins
SEG_AFLAGS="-c:a pcm_s16le"

# Source frame rate — used to normalize all Step 2 segments before concat
SFPS=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=avg_frame_rate -of default=nw=1:nk=1 current.MOV)
```

`$VFLAGS` — GPU encoder if usable, falls back to CPU libx264. Quality equivalent: `-cq 18` ≈ `-crf 18`.

`$SEG_AFLAGS` — use uncompressed PCM for intermediate segment files so concat does not preserve per-segment AAC delay/padding.

`$SFPS` — exact source playback fps as a rational string (e.g. `30000/1001`). Used in Step 2 to normalize every segment to the same fps before the concat demuxer.

---

## Step 1 — Cut segments / mute sections

One ffmpeg call per segment — avoids loading multiple decode streams into memory (prevents OOM on large/4K files).

```bash
# Example: keep 0–13, mute 13–17, keep 17–53, skip 53–66, keep 66+

ffmpeg -i current.MOV \
  -filter_complex "[0:v]trim=start=0:end=13,setpts=PTS-STARTPTS[v];[0:a]atrim=start=0:end=13,asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" $VFLAGS $SEG_AFLAGS seg_01.MOV -y \
  || { echo "STEP 1 seg 1 FAILED"; exit 1; }

ffmpeg -i current.MOV \
  -filter_complex "[0:v]trim=start=13:end=17,setpts=PTS-STARTPTS[v];[0:a]atrim=start=13:end=17,asetpts=PTS-STARTPTS,volume=0[a]" \
  -map "[v]" -map "[a]" $VFLAGS $SEG_AFLAGS seg_02.MOV -y \
  || { echo "STEP 1 seg 2 FAILED"; exit 1; }

ffmpeg -i current.MOV \
  -filter_complex "[0:v]trim=start=17:end=53,setpts=PTS-STARTPTS[v];[0:a]atrim=start=17:end=53,asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" $VFLAGS $SEG_AFLAGS seg_03.MOV -y \
  || { echo "STEP 1 seg 3 FAILED"; exit 1; }

# segment 53–66 is skipped — no ffmpeg call for it

ffmpeg -i current.MOV \
  -filter_complex "[0:v]trim=start=66,setpts=PTS-STARTPTS[v];[0:a]atrim=start=66,asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" $VFLAGS $SEG_AFLAGS seg_04.MOV -y \
  || { echo "STEP 1 seg 4 FAILED"; exit 1; }

# Join with concat demuxer
printf "file '%s'\n" seg_01.MOV seg_02.MOV seg_03.MOV seg_04.MOV > seg_list.txt
ffmpeg -f concat -safe 0 -i seg_list.txt -c:v copy -c:a aac next.MOV -y \
  || { echo "STEP 1 concat FAILED"; exit 1; }
mv next.MOV current.MOV
rm -f seg_01.MOV seg_02.MOV seg_03.MOV seg_04.MOV seg_list.txt
```

**Rules:**
- `trim` / `atrim` + `setpts` / `asetpts` = timestamp-accurate segment boundaries without keyframe drift
- `volume=0` after `atrim` = mute only that segment's audio
- Skipped ranges = no ffmpeg call for that range, just omit it from the list
- Intermediate audio stays PCM, then concat re-encodes audio once to AAC for the final file without per-segment AAC splice artifacts

---

## Step 2 — Smooth slow-motion

One ffmpeg call per segment — minterpolate only on the affected segment, not the whole file.

```bash
# Example: slow-mo from 0:30 to 0:35 at 0.5x speed

ffmpeg -i current.MOV \
  -filter_complex "[0:v]trim=start=0:end=30,setpts=PTS-STARTPTS,fps=$SFPS[v];[0:a]atrim=start=0:end=30,asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" $VFLAGS $SEG_AFLAGS seg_01.MOV -y \
  || { echo "STEP 2 seg 1 FAILED"; exit 1; }

ffmpeg -i current.MOV \
  -filter_complex "[0:v]trim=start=30:end=35,setpts=PTS-STARTPTS,minterpolate=fps=60:mi_mode=mci,setpts=2*PTS,fps=$SFPS,drawtext=text='0.5x':fontsize=40:fontcolor=white:x=w-tw-30:y=30:shadowcolor=black:shadowx=2:shadowy=2[v];[0:a]atrim=start=30:end=35,asetpts=PTS-STARTPTS,atempo=0.5[a]" \
  -map "[v]" -map "[a]" $VFLAGS $SEG_AFLAGS seg_02.MOV -y \
  || { echo "STEP 2 seg 2 FAILED"; exit 1; }

ffmpeg -i current.MOV \
  -filter_complex "[0:v]trim=start=35,setpts=PTS-STARTPTS,fps=$SFPS[v];[0:a]atrim=start=35,asetpts=PTS-STARTPTS[a]" \
  -map "[v]" -map "[a]" $VFLAGS $SEG_AFLAGS seg_03.MOV -y \
  || { echo "STEP 2 seg 3 FAILED"; exit 1; }

printf "file '%s'\n" seg_01.MOV seg_02.MOV seg_03.MOV > seg_list.txt
ffmpeg -f concat -safe 0 -i seg_list.txt -c:v copy -c:a aac next.MOV -y \
  || { echo "STEP 2 concat FAILED"; exit 1; }
mv next.MOV current.MOV
rm -f seg_01.MOV seg_02.MOV seg_03.MOV seg_list.txt
```

**Key flags:**
 - `minterpolate=fps=60` — generates frames to 60fps before slowing; `fps=$SFPS` then returns the segment to the source playback fps for concat
- `mi_mode=mci` — motion compensated interpolation (best quality)
- `setpts=2*PTS` — 0.5x speed. Use `setpts=4*PTS` for 0.25x
- `fps=$SFPS` on every Step 2 segment — normalizes all intermediates to one exact nominal fps before concat
- `atempo=0.5` — slows audio. Chain two for 0.25x: `atempo=0.5,atempo=0.5` (atempo range: 0.5–2.0)
- Overlay is inline in `drawtext` — show the speed value only, e.g. `0.5x` or `2x`

**Speed reference:**

| Effect | `setpts` | `atempo` | Label |
|--------|----------|----------|-------|
| 0.5x slow | `setpts=2*PTS` | `atempo=0.5` | `0.5x` |
| 0.25x slow | `setpts=4*PTS` | `atempo=0.5,atempo=0.5` | `0.25x` |
| 2x fast | `setpts=0.5*PTS` | `atempo=2.0` | `2x` |
| 4x fast | `setpts=0.25*PTS` | `atempo=2.0,atempo=2.0` | `4x` |

---

## Step 3 — Audio normalization

```bash
ffmpeg -i current.MOV -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy next.MOV -y \
  || { echo "STEP 3 FAILED"; exit 1; }
mv next.MOV current.MOV
```

- `I=-16` — target loudness (LUFS), standard for online video
- `TP=-1.5` — true peak ceiling to prevent clipping
- `LRA=11` — loudness range (dynamic variation)
- `-c:v copy` — video untouched, audio only re-encoded

---

## Step 4 — Social reframing

```bash
# TikTok / Reels — 9:16 (iPhone MOV is already 9:16, no reframing needed)
ffmpeg -i current.MOV -vf "crop=ih*9/16:ih,scale=1080:1920" $VFLAGS -c:a aac next.MOV -y \
  || { echo "STEP 4 FAILED"; exit 1; }
mv next.MOV current.MOV

# YouTube — 16:9
ffmpeg -i current.MOV -vf "crop=iw:iw*9/16,scale=1920:1080" $VFLAGS -c:a aac next.MOV -y \
  || { echo "STEP 4 FAILED"; exit 1; }
mv next.MOV current.MOV

# Instagram — 1:1 (min dimension crop — works on both portrait and landscape)
ffmpeg -i current.MOV -vf "crop=min(iw\,ih):min(iw\,ih),scale=1080:1080" $VFLAGS -c:a aac next.MOV -y \
  || { echo "STEP 4 FAILED"; exit 1; }
mv next.MOV current.MOV
```

| Platform | Aspect Ratio | Resolution |
|----------|-------------|------------|
| TikTok / Reels | 9:16 | 1080×1920 |
| YouTube | 16:9 | 1920×1080 |
| Instagram | 1:1 | 1080×1080 |

---

## Step 7 — Burn captions

*(Steps 5 and 6 — transcribe with WhisperX + generate captions .ass file — are in captions-reference.md)*

Burn captions only:
```bash
ffmpeg -i current.MOV -vf "ass=captions.ass" $VFLAGS -c:a aac -b:a 128k output.MOV -y \
  || { echo "STEP 7 FAILED"; exit 1; }
```

Burn captions + reframe in one pass:
```bash
ffmpeg -i current.MOV -vf "crop=ih*9/16:ih,scale=1080:1920,ass=captions.ass" $VFLAGS -c:a aac -b:a 128k output.MOV -y \
  || { echo "STEP 7 FAILED"; exit 1; }
```

- `-cq/-crf 18` — high quality (18–23 is typical; lower = better; set via `$VFLAGS`)
- Processing speed: ~10x realtime on this machine

---

## Video Info (iPhone MOV)

- Resolution: 720×1280 (portrait, 9:16)
- Video: h264 High, ~3510 kb/s, 29.98 fps
- Audio: AAC LC, 44100 Hz, stereo, ~126 kb/s
