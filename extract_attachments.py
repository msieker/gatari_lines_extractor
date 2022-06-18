"""
Extracts attachments from a list of episodes
"""
from os import path
import csv
import json
from pathlib import Path
import subprocess
from typing import Any, List
from models import EpisodeInfo
ROOT_PATH = Path("/mnt/e/gatari_lines")
SOURCE_PATH = ROOT_PATH / Path("source")
EPISODES_FILE = SOURCE_PATH / "Episodes.csv"
OUTPUT_PATH = ROOT_PATH / Path("mediainfo")
FONT_TYPES = ["application/x-truetype-font", "application/vnd.ms-opentype", "font/ttf", "font/otf"]

SUB_MAP = {
    "SubRip/SRT": "srt",
    "VobSub": "sub",
    "SubStationAlpha": "ssa"
}

def get_mkv_data(file_path: Path):
    """
    Runs mkvmerge on a file, returning the JSON it outputs
    """
    information = json.loads(subprocess.check_output([
        "mkvmerge",
        "--identify",
        "-J",
        file_path]).decode())
    return information

def extract_fonts(episode_info: EpisodeInfo, media_info: Any):
    """
    Extracts fonts from an MKV file
    """
    font_path = episode_info.episode_path / "fonts"
    font_path.mkdir(parents=True, exist_ok=True)

    font_list = {
        a["id"]: font_path / a["file_name"]
        for a in media_info["attachments"] if a["content_type"] in FONT_TYPES
    }

    if not all((v.exists() for k, v in font_list.items())):
        args = [
            "mkvextract",
            "attachments",
            str(episode_info.file_path)] + [f"{k}:{str(v)}" for k, v in font_list.items()]
        subprocess.run(args, check=True)

def extract_subtitles(episode_info: EpisodeInfo, media_info: Any):
    """
    Extracts subtitles from an mkv file
    """
    sub_path = episode_info.episode_path / "subs"
    sub_path.mkdir(parents=True, exist_ok=True)

    sub_map = [{
        'file_name': str(sub_path / (
            str(t["id"]) + "_" +
            t["properties"]["language"] +
            "." + SUB_MAP[t["codec"]])),
        'language': t["properties"]["language"],
        'info': t,
        'track': t['id']
    } for t in media_info["tracks"] if t["type"] == "subtitles"]

    if len(sub_map) > 0:
        args = [
            "mkvextract",
            "tracks",
            str(episode_info.file_path)]
        args = args + [f"{i['track']}:{i['file_name']}" for i in sub_map]
        subprocess.run(args, check=True)

    with open(episode_info.episode_path / 'subs.json', "w", encoding="utf8") as out_file:
        json.dump(sub_map, out_file, indent=2)

def load_episodes() -> List[EpisodeInfo]:
    """
    Reads Episodes.csv and returns a list of episode info dataclasses
    """
    all_lines: List[EpisodeInfo] = []
    with open(EPISODES_FILE, "r", encoding="utf8") as in_csv:
        reader = csv.DictReader(in_csv)

        for line in reader:
            all_lines.append(EpisodeInfo(
                line["File Name"],
                int(line["Series Order"]),
                line["Series Name"],
                int(line["Episode Number"]),
                int(line["Overall Order"]),
                SOURCE_PATH / line["File Name"],
                OUTPUT_PATH / path.basename(path.splitext(line["File Name"])[0])
            ))
    return all_lines

def process_episode(episode_info: EpisodeInfo):
    """
    Processes an individual episode, extracting any attachments to the video file
    """
    print(f"Processing episode {episode_info.file_name}")
    episode_info.episode_path.mkdir(parents=True, exist_ok=True)
    if (episode_info.episode_path / '.completed').exists():
        print(f"{episode_info.file_name} marked as completed, skipping.")
        return

    media_info = get_mkv_data(episode_info.file_path)

    mediainfo_path = episode_info.episode_path / Path("mediainfo.json")
    with open(mediainfo_path, "w", encoding="utf8") as out_file:
        json.dump(media_info, out_file, indent=2)

    extract_fonts(episode_info, media_info)
    extract_subtitles(episode_info, media_info)

    with open(episode_info.episode_path / 'episode_info.json', "w", encoding="utf8") as out_file:
        json.dump(episode_info.as_json_dict(), out_file, indent=2)
    (episode_info.episode_path / '.completed').touch()

def main():
    """
    Reads from an Episodes.csv found the the source directory, and then runs
    mkvmerge to extract the media info and attachments from the file, and saves
    them to a per-episode path in the mediainfo directory
    """
    episodes = load_episodes()

    for i in episodes:
        process_episode(i)

if __name__ == "__main__":
    main()
