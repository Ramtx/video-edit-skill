# Captions Reference (WhisperX + ASS)

---

## Step 5 — Transcribe with WhisperX

```bash
mkdir -p /tmp/whisperx_out
whisperx current.MOV --model base --output_format json --output_dir /tmp/whisperx_out
```

- Output: `/tmp/whisperx_out/<input_basename>.json` — WhisperX names the file after the input. So `current.MOV` → `/tmp/whisperx_out/current.json`. Always derive the path from the actual input filename, never hardcode `video.json`.
- JSON structure: `{ "segments": [ { "words": [ { "word": "Go", "start": 0.271, "end": 0.431, "score": 0.878 } ] } ] }`
- Some words miss `start`/`end` if alignment failed — always filter them out
- `--word_timestamps True` is NOT a valid flag — word timing is always included
- `torchcodec` warning in logs is harmless — WhisperX still works fine
- Confirm detected language in logs before proceeding

---

## Step 6 — Generate ASS captions (make_captions.py)

Run the tool:
```bash
python3 ~/tools/make_captions.py \
  --input /tmp/whisperx_out/current.json \
  --output captions.ass \
  --active-color yellow \
  --inactive-color white \
  --position bottom \
  --fontsize 44
```

All caption logic (word grouping, ASS formatting, escape handling) lives in `~/tools/make_captions.py`. Read that file if you need to understand or debug the internals.

---

## Color Reference

ASS format uses `&HBBGGRR&` (6 hex) in override tags (`\1c`), and `&HAABBGGRR&` (8 hex, with alpha prefix) in Style definitions. **BGR not RGB.** Alpha: `00` = opaque, `FF` = transparent.

| Color name | Override tag value | Style definition value |
|------------|--------------------|----------------------|
| White | `&HFFFFFF&` | `&H00FFFFFF&` |
| Yellow | `&H00FFFF&` | `&H0000FFFF&` |
| Cyan | `&HFFFF00&` | `&H00FFFF00&` |
| Red | `&H0000FF&` | `&H000000FF&` |
| Black | `&H000000&` | `&H00000000&` |

## Position Reference

Set in the ASS Style `Alignment` field:

| User says | Alignment value |
|-----------|----------------|
| bottom (default) | `2` |
| middle | `5` |
| top | `8` |

`MarginV=80` = 80px from the edge. Adjust for different placements.

## Font Size

Default: **44** for 720×1280 portrait. Scale proportionally for other resolutions (e.g. 1080p → ~66).
