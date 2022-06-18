"""
Processes ASS subtitles into a de-cluttered JSON format used by grab_frames.py
"""
import itertools
from os import path
import glob
import json
from pathlib import Path
import re
from itertools import groupby
from dataclasses import asdict
from typing import Any, List, Optional, Set
from models import SubtitleLine
SUB_VERSION = 1
ROOT_PATH = Path("/mnt/e/gatari_lines")
SOURCE_PATH = ROOT_PATH / Path("source")
EPISODES_FILE = SOURCE_PATH / "Episodes.csv"
OUTPUT_PATH = ROOT_PATH / Path("mediainfo")
FONT_TYPES = ["application/x-truetype-font", "application/vnd.ms-opentype"]

SUB_MAP = {
    "SubRip/SRT": "srt",
    "VobSub": "sub",
    "SubStationAlpha": "ssa"
}

TIMESTAMP = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{2,3})")

STRIP_SLASH = re.compile(r"(\\.)")

COLLAPSE_WHITESPACE = re.compile(r"\s+")


ranges = [
    {"from": ord("\u3300"), "to": ord("\u33ff")},         # compatibility ideographs
    {"from": ord("\ufe30"), "to": ord("\ufe4f")},         # compatibility ideographs
    {"from": ord("\uf900"), "to": ord("\ufaff")},         # compatibility ideographs
    {"from": ord("\U0002F800"), "to": ord("\U0002fa1f")}, # compatibility ideographs
    {'from': ord('\u3040'), 'to': ord('\u309f')},         # Japanese Hiragana
    {"from": ord("\u30a0"), "to": ord("\u30ff")},         # Japanese Katakana
    {"from": ord("\u2e80"), "to": ord("\u2eff")},         # cjk radicals supplement
    {"from": ord("\u4e00"), "to": ord("\u9fff")},
    {"from": ord("\u3400"), "to": ord("\u4dbf")},
    {"from": ord("\U00020000"), "to": ord("\U0002a6df")},
    {"from": ord("\U0002a700"), "to": ord("\U0002b73f")},
    {"from": ord("\U0002b740"), "to": ord("\U0002b81f")},
    {"from": ord("\U0002b820"), "to": ord("\U0002ceaf")}  # included as of Unicode 8.0
]

def is_cjk(char) -> bool:
    """
    Returns true if a character is CJK
    """
    return any((range["from"] <= ord(char) <= range["to"] for range in ranges))

def is_cjk_string(string) -> bool:
    """
    Returns true if a string is entirely made of CJK characters
    """
    return any([is_cjk(c) for c in string])

def deal_with_whitespace(string) -> str:
    """
    If the string is a CJK string, strip all whitespace, if it has
    latin text, collapse multiple whitespace characters down to a single space
    """
    if is_cjk_string(string):
        return "".join(string.split())
    return collapse_whitespace_characters(string)

def collapse_whitespace_characters(raw_text) -> str:
    """
    Collapses multiple whitespace characters down to a single space
    """
    ret = ''
    if len(raw_text) > 1:
        prev_char = raw_text[0]
        ret += prev_char
        for cur_char in raw_text[1:]:
            if not cur_char.isspace() or cur_char != prev_char:
                ret += cur_char
            prev_char = cur_char
    else:
        ret = raw_text
    return ret

def timestamp_to_ms(timestamp: str) -> int:
    """
    Converts a timestamp in the format of 00:00:00.0 to milliseconds
    """
    matches = TIMESTAMP.match(timestamp)

    if not matches:
        return 0
    groups = matches.groups()
    hours, minutes, seconds, frac = map(int, groups)
    milliseconds = frac * 10**(3 - len(groups[-1]))
    milliseconds += seconds * 1000
    milliseconds += minutes * 60000
    milliseconds += hours * 3600000
    return milliseconds

def get_unbracketed_text(string: str) -> str:
    """
    Strips formatting commands from a subtitle line
    """
    bracket_count = 0
    out_text = ""
    bracketed_text = ""
    is_drawing = False

    for _, char in enumerate(string):
        if char == "{":
            bracket_count += 1
            bracketed_text = ""
        elif char == "}":
            bracket_count -= 1

            if "\\p1" in bracketed_text:
                is_drawing = True
            if "\\p2" in bracketed_text:
                is_drawing = True
            if "\\p3" in bracketed_text:
                is_drawing = True
            if "\\p4" in bracketed_text:
                is_drawing = True
            if "\\p0" in bracketed_text:
                is_drawing = False
        else:
            if bracket_count == 0 and not is_drawing:
                out_text += char
            else:
                bracketed_text += char

    return out_text

def extract_ass_subtext(sub_path: Path) -> List[SubtitleLine]:
    """
    Extract actual subtitle text from an ASS file, stripped of
    formatting commands
    """
    sub_lines: List[SubtitleLine] = []
    with open(sub_path, "r", encoding="utf8") as sub_file:
        all_lines = sub_file.readlines()

    dialog_lines = [l for l in all_lines if l.startswith("Dialogue")]

    for line in dialog_lines:
        parts = line.split(",", 9)
        sub = parts[-1].strip() #STRIP_SLASH.sub("", parts[-1])
        sub_text = get_unbracketed_text(sub).strip() \
            .replace("\\N", "\n").replace("\\n", "\n").replace("\\h", " ")

        if sub_text:
            sub_lines.append(SubtitleLine(
                start = parts[1],
                start_ms = timestamp_to_ms(parts[1]),
                end = parts[2],
                end_ms = timestamp_to_ms(parts[2]),
                raw_subs = tuple([sub]),
                text = deal_with_whitespace(sub_text)
            ))
    return sorted(sub_lines, key=lambda k: k.start_ms)

# I don't think this is needed with the new CombineLines function, but keep it here for reference
# def collapse_duplicate_subs(in_subtext: List[SubtitleLine]) -> List[SubtitleLine]:
#     """
#     Collapse repeated subtitle text (often done by fansubbers showing off with styling)
#     to a single subtitle
#     """
#     out_subtext = []

#     line: SubtitleLine | None = None
#     for l in in_subtext:
#         if not line:
#             line = SubtitleLine(
#                 l.start, l.start_ms,
#                 l.end, l.end_ms,
#                 l.raw_subs, l.text)
#         else:
#             if line.text == l.text and (l.start_ms - line.end_ms) < 100:
#                 line.end_ms = l.end_ms
#                 line.end = l.end
#             else:
#                 out_subtext.append(line)
#                 line = SubtitleLine(
#                 l.start, l.start_ms,
#                 l.end, l.end_ms,
#                 l.raw_subs, l.text)
#     if line:
#         out_subtext.append(line)

#     return out_subtext

def get_unique_subs(subs: list[str]):
    """
    Returns unique strings from a list of strings
    """
    seen: Set[str] = set()
    seen_add = seen.add
    return [x for x in subs if not (x in seen or seen_add(x))]

def collapse_by_time(in_subtext: List[SubtitleLine]) -> List[SubtitleLine]:
    """
    When multiple subtitles start at the same time, combine all of their (unique)
    text together into one "subtitle"
    """
    out_subtext: List[SubtitleLine] = []
    for _, items in groupby(in_subtext, lambda s: s.start_ms):
        item_list = list(items)
        all_text = get_unique_subs([deal_with_whitespace(t.text) for t in item_list])
        sub = item_list[0]
        out_subtext.append(SubtitleLine(
            start = sub.start,
            start_ms = sub.start_ms,
            end = sub.end,
            end_ms = sub.end_ms,
            text = "\n".join(all_text),
            raw_subs= tuple(itertools.chain.from_iterable((s.raw_subs for s in item_list)))
        ))
    return out_subtext


def combine_lines(in_subtext: List[SubtitleLine]) -> List[SubtitleLine]:
    """
    Looks through all subtitles for lines with the same text with adjoining end and start times,
    and combines them into one
    """
    remaining_lines = list(in_subtext)
    processed: List[SubtitleLine] = []

    def next_line_filter(next_line: Optional[SubtitleLine], this_line: Optional[SubtitleLine]):
        if this_line is None or next_line is None:
            return False
        return next_line.start_ms == this_line.end_ms and next_line.text == this_line.text

    while remaining_lines:
        this_line = remaining_lines.pop(0)

        touched_lines: List[SubtitleLine] = []

        next_line: Optional[SubtitleLine] = this_line
        while next_line := next(filter(lambda l: next_line_filter(l, next_line), remaining_lines), None):
            touched_lines.append(next_line)

        if touched_lines:
            last_line = max(touched_lines, key=lambda l: l.end_ms)
            processed.append(SubtitleLine(
                this_line.start,
                this_line.start_ms,
                last_line.end,
                last_line.end_ms,
                raw_subs=tuple(itertools.chain.from_iterable([this_line.raw_subs] + [l.raw_subs for l in touched_lines])),
                text=this_line.text
            ))
            remaining_lines = [l for l in remaining_lines if l not in touched_lines]
        else:
            processed.append(this_line)

    return processed

def process_ass(sub_path: Path) -> List[SubtitleLine]:
    """
    Processes a subtitle file, returning processed subtitle text
    """
    print("Processing", sub_path)
    raw_subtext = extract_ass_subtext(sub_path)
    subtext = collapse_by_time(combine_lines(raw_subtext))
    return sorted(subtext, key=lambda k: k.start_ms)

def process_sub(episode_dir: Path, track_info: Any, force=True):
    """
    Processes a subtitle file,
    """
    ass_path = Path(track_info["file_name"])
    sub_path = ass_path.parent

    subs_json = sub_path / f"{track_info['track']}_{track_info['language']}.json"

    if not (force or subs_json.exists()):
        try:
            with open(subs_json, "r", encoding="utf8") as subs_json_file:
                existing_info = json.load(subs_json_file)
            if existing_info["subversion"] == SUB_VERSION and existing_info["source"] == str(sub_path):
                print(f"Skipping {episode_dir}. Already has subs")
                return
        except: # pylint: disable=bare-except
            print("Invalid JSON, reprocessing")

    subtitles = []
    if track_info["info"]["properties"]["codec_id"] == "S_TEXT/ASS":
        subtitles = process_ass(ass_path)

    with open(subs_json, "w", encoding="utf8") as subs_json_file:
        json.dump({
            "source": str(ass_path),
            "subversion": SUB_VERSION,
            "subs": [asdict(s) for s in subtitles]
            }, subs_json_file , indent=4)

def process_episode(episode_dir: Path):
    """
    Processes subtitles for an episode
    """

    with open(episode_dir / Path("subs.json"), "r", encoding="utf8") as subs_file:
        subs_info = json.load(subs_file)

    for track in subs_info:
        process_sub(episode_dir, track, False)

def get_episode_dirs():
    """
    Finds episode directories (those containing episode_info.json files)
    """
    dirs = []
    for episode_info_filename in glob.glob(path.join(OUTPUT_PATH, "**", "episode_info.json")):
        dirs.append(Path(episode_info_filename).parent)

    return dirs

if __name__ == "__main__":
    for episodes in get_episode_dirs():
        process_episode(episodes)

# extracted = combine_lines(extract_ass_subtext(Path('test3.sorted.ass'))[:20])
# print(extracted)
