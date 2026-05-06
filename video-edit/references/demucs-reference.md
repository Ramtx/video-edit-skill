# Demucs Reference (Audio Cleanup)

Demucs is an AI source separation model by Meta Research. It isolates the primary voice from background noise, ambient sounds, other voices, traffic, etc.

---

## Step 3 — Audio cleanup with Demucs

**Important:** Always use `python3.12` to run demucs — the system `python3` may point to a different version without torch/demucs installed.

### Detect device (GPU vs CPU)

```bash
DEMUCS_DEVICE=$(python3.12 -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')" 2>/dev/null || echo "cpu")
```

### Extract audio, run Demucs, replace audio

```bash
# Extract audio from current video
ffmpeg -i current.MOV -vn -c:a pcm_s16le -ar 44100 audio_full.wav -y \
  || { echo "STEP 3 extract FAILED"; exit 1; }

# Run Demucs — isolate vocals (two-stems mode: vocals vs everything else)
python3.12 -m demucs --two-stems vocals -n htdemucs --device $DEMUCS_DEVICE -o demucs_out audio_full.wav \
  || { echo "STEP 3 demucs FAILED"; exit 1; }

# Replace video audio with isolated vocals
ffmpeg -i current.MOV -i demucs_out/htdemucs/audio_full/vocals.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -shortest next.MOV -y \
  || { echo "STEP 3 replace FAILED"; exit 1; }
mv next.MOV current.MOV

# Cleanup intermediate files
rm -rf demucs_out audio_full.wav
```

---

## How it works

- `--two-stems vocals` splits audio into two tracks: **vocals** (the speaker) and **no_vocals** (everything else — truck noise, background voices, ambient sound)
- Only the `vocals.wav` track is kept; the rest is discarded
- Model `htdemucs` (Hybrid Transformer Demucs) gives the best quality

## Output structure

```
demucs_out/htdemucs/audio_full/
  vocals.wav      # isolated voice — use this
  no_vocals.wav   # everything else — discard
```

The output filenames match the input: `audio_full.wav` → folder `audio_full/`.

## Performance

| Device | ~2 min audio |
|--------|-------------|
| CPU | ~36 seconds |
| GPU (RTX 4050) | ~5 seconds |

## Notes

- Demucs runs on PyTorch — uses GPU automatically when `--device cuda` is set and CUDA is available
- The `htdemucs` model downloads once (~80 MB) to `~/.cache/torch/hub/checkpoints/` and is reused
- Background voices are usually classified as "no_vocals" when they are faint/ambient — Demucs is effective at removing them
- Run this step BEFORE audio normalization (Step 4) — normalize the clean audio, not the noisy original
- torchcodec warnings in logs are harmless
