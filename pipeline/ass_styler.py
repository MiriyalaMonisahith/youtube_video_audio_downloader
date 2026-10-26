"""
Advanced SubStation Alpha (.ass) subtitle styler for YouTube Shorts.
Generates animated, word-by-word karaoke-style captions positioned
at the bottom of 9:16 vertical video with customizable styles
(MrBeast Yellow, Hormozi Cyan, Neon Red, Minimal Clean).
"""

from typing import List, Dict, Any
import os

STYLES = {
    "mrbeast": {
        "name": "MrBeast",
        "fontname": "Montserrat",
        "fontsize": 54,
        "primary_color": "&H00FFFFFF",      # Inactive: crisp white
        "highlight_color": "&H0000E6FF",    # Active: vibrant yellow (&HAABBGGRR)
        "outline_color": "&H00000000",      # Thick black outline
        "back_color": "&H80000000",         # Semi-transparent shadow
        "bold": 1,
        "italic": 0,
        "border_style": 1,                  # 1 = outline + shadow
        "outline": 4.0,
        "shadow": 2.0,
        "alignment": 2,                     # 2 = Bottom-Center
        "margin_v": 190,                    # Safe zone from bottom in 1920p
    },
    "hormozi": {
        "name": "Hormozi",
        "fontname": "Impact",
        "fontsize": 58,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FF00",    # Vibrant green
        "outline_color": "&H00000000",
        "back_color": "&HB0000000",
        "bold": 1,
        "italic": 0,
        "border_style": 3,                  # 3 = opaque backing box
        "outline": 3.0,
        "shadow": 0.0,
        "alignment": 2,
        "margin_v": 190,
    },
    "neon": {
        "name": "Neon Red",
        "fontname": "Montserrat",
        "fontsize": 52,
        "primary_color": "&H00F0F0F0",
        "highlight_color": "&H003333FF",    # Electric Red / Hot Pink
        "outline_color": "&H00101010",
        "back_color": "&H90200050",
        "bold": 1,
        "italic": 0,
        "border_style": 1,
        "outline": 3.5,
        "shadow": 3.0,
        "alignment": 2,
        "margin_v": 190,
    },
    "clean": {
        "name": "Minimal Clean",
        "fontname": "Arial",
        "fontsize": 48,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H00D0FFFF",    # Soft warm white
        "outline_color": "&H00111111",
        "back_color": "&H60000000",
        "bold": 1,
        "italic": 0,
        "border_style": 1,
        "outline": 2.5,
        "shadow": 1.5,
        "alignment": 2,
        "margin_v": 190,
    }
}


def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format: H:MM:SS.cs"""
    seconds = max(0.0, seconds)
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


def build_ass_header(style_config: Dict[str, Any], width: int = 1080, height: int = 1920) -> str:
    """Build ASS file script info and style header."""
    header = f"""[Script Info]
Title: Auto-Generated Shorts Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_config['fontname']},{style_config['fontsize']},{style_config['primary_color']},&H000000FF,{style_config['outline_color']},{style_config['back_color']},{style_config['bold']},{style_config['italic']},0,0,100,100,0,0,{style_config['border_style']},{style_config['outline']},{style_config['shadow']},{style_config['alignment']},40,40,{style_config['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header


def generate_animated_ass(
    words: List[Dict[str, Any]],
    output_path: str,
    clip_start: float = 0.0,
    clip_end: float = 60.0,
    style_name: str = "mrbeast",
    max_words_per_group: int = 4
) -> str:
    """
    Generate an animated ASS subtitle file where each spoken word lights up
    in the style's highlight color as it is spoken.
    
    words: list of dicts with {'word', 'start', 'end'}
    clip_start: start offset to subtract from word timestamps
    clip_end: end offset
    """
    style = STYLES.get(style_name.lower(), STYLES["mrbeast"])
    
    # Filter words strictly inside [clip_start, clip_end]
    valid_words = []
    for w in words:
        w_start = w.get("start", 0.0)
        w_end = w.get("end", 0.0)
        if w_end > clip_start and w_start < clip_end:
            valid_words.append({
                "word": w.get("word", "").strip(),
                "start": max(0.0, w_start - clip_start),
                "end": max(0.0, min(w_end - clip_start, clip_end - clip_start))
            })
            
    if not valid_words:
        # Fallback: create empty ass file
        content = build_ass_header(style)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    # Chunk words into small rhythmic groups (3-5 words)
    groups = []
    curr_group = []
    for w in valid_words:
        curr_group.append(w)
        if len(curr_group) >= max_words_per_group or w["word"].endswith((".", "!", "?")):
            groups.append(curr_group)
            curr_group = []
    if curr_group:
        groups.append(curr_group)

    events = []
    hl_color = style["highlight_color"]
    prim_color = style["primary_color"]

    for group in groups:
        if not group:
            continue
        # For each word in the group, create a dialogue event during its duration
        # highlighting that specific word while keeping other words in primary color.
        for active_idx, active_word in enumerate(group):
            w_start = active_word["start"]
            w_end = active_word["end"]
            
            # Ensure non-zero duration
            if w_end <= w_start:
                w_end = w_start + 0.25

            start_str = format_ass_time(w_start)
            end_str = format_ass_time(w_end)

            line_parts = []
            for idx, w in enumerate(group):
                clean_w = w["word"].replace("{", "").replace("}", "")
                if idx == active_idx:
                    # Highlight active word with scale pop effect and highlight color
                    line_parts.append(r"{\1c" + hl_color + r"\fscx110\fscy110}" + clean_w + r"{\fscx100\fscy100\1c" + prim_color + r"}")
                else:
                    line_parts.append(clean_w)

            formatted_text = " ".join(line_parts)
            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{formatted_text}")

    full_ass = build_ass_header(style) + "\n".join(events) + "\n"
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_ass)

    return output_path
