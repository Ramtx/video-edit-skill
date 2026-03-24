#!/usr/bin/env python3
"""Generate ASS subtitle file with per-word highlight from WhisperX JSON.

Usage:
  python3 make_captions.py --input transcript.json --output captions.ass
  python3 make_captions.py --input transcript.json --output captions.ass \
      --active-color yellow --inactive-color white --position bottom --fontsize 44
"""

import argparse
import json

# ASS color format: &HBBGGRR& (BGR, not RGB). Alpha: 00=opaque, FF=transparent.
COLOR_MAP = {
    'yellow': r'{\1c&H00FFFF&\1a&H00&\3a&HFF&\bord0\blur0\shad0}',
    'white':  r'{\1c&HFFFFFF&\1a&H00&\3a&HFF&\bord0\blur0\shad0}',
    'cyan':   r'{\1c&HFFFF00&\1a&H00&\3a&HFF&\bord0\blur0\shad0}',
    'red':    r'{\1c&H0000FF&\1a&H00&\3a&HFF&\bord0\blur0\shad0}',
}

ALIGNMENT_MAP = {'bottom': 2, 'middle': 5, 'top': 8}

def escape_ass(text):
    """Escape characters that ASS interprets as override syntax."""
    text = text.replace('\\', '\\\\')
    text = text.replace('{', '\\{')
    text = text.replace('}', '\\}')
    return text

def to_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def main():
    parser = argparse.ArgumentParser(description='Generate ASS captions from WhisperX JSON')
    parser.add_argument('--input',          required=True,  help='Path to WhisperX JSON file')
    parser.add_argument('--output',         required=True,  help='Path to output .ass file')
    parser.add_argument('--active-color',   default='yellow', choices=COLOR_MAP.keys(), help='Color of the spoken word')
    parser.add_argument('--inactive-color', default='white',  choices=COLOR_MAP.keys(), help='Color of non-spoken words')
    parser.add_argument('--position',       default='bottom', choices=ALIGNMENT_MAP.keys(), help='Caption position')
    parser.add_argument('--fontsize',       default=44,  type=int, help='Font size (default: 44)')
    parser.add_argument('--margin-v',       default=80,  type=int, help='Margin from edge in px (default: 80)')
    parser.add_argument('--play-res-x',     default=720, type=int, help='Video width for ASS coordinate space (default: 720)')
    parser.add_argument('--play-res-y',     default=1280, type=int, help='Video height for ASS coordinate space (default: 1280)')
    parser.add_argument('--max-chars',      default=30,  type=int, help='Max characters per caption line (default: 30)')
    args = parser.parse_args()

    try:
        with open(args.input, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: input file not found: {args.input}")
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse JSON from {args.input}: {e}")
        raise SystemExit(1)

    active_tag   = COLOR_MAP[args.active_color]
    inactive_tag = COLOR_MAP[args.inactive_color]
    alignment    = ALIGNMENT_MAP[args.position]

    # Group words into lines by character count
    lines = []
    for seg in data['segments']:
        words = [w for w in seg.get('words', []) if 'start' in w and 'end' in w]
        if not words:
            continue
        chunk, char_count = [], 0
        for w in words:
            wlen = len(w['word'].strip())
            if chunk and char_count + wlen + 1 > args.max_chars:
                lines.append(chunk)
                chunk, char_count = [], 0
            chunk.append(w)
            char_count += wlen + 1
        if chunk:
            lines.append(chunk)

    ass_events = []
    for line_words in lines:
        for i, active_word in enumerate(line_words):
            word_start = active_word['start']
            word_end = line_words[i + 1]['start'] if i + 1 < len(line_words) else active_word['end']
            parts = []
            for j, w in enumerate(line_words):
                text = escape_ass(w['word'].strip())
                tag = active_tag if j == i else inactive_tag
                parts.append(tag + text + r'{\r}')
            ass_events.append(
                f"Dialogue: 0,{to_ass_time(word_start)},{to_ass_time(word_end)},"
                f"Default,,0,0,0,," + ' '.join(parts)
            )

    ass_content = f"""\
[Script Info]
ScriptType: v4.00+
PlayResX: {args.play_res_x}
PlayResY: {args.play_res_y}
Collisions: Normal
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{args.fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,2,0,{alignment},30,30,{args.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + '\n'.join(ass_events)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    print(f"Written {len(ass_events)} caption events to {args.output}")

if __name__ == '__main__':
    main()
