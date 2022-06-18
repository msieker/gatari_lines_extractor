"""
Uses ffmpeg to decode video files, saving out frames where the time of the
frame is in the middle of when a subtitle should be on screen
"""
from os import path
import glob
import json
from pathlib import Path
from dataclasses import asdict
from typing import List
import av
from av.filter import Graph

from models import EpisodeInfo, SubtitleLine, ExtractedFrame
SUB_VERSION = 1
ROOT_PATH = Path("/mnt/e/gatari_lines")
SOURCE_PATH = ROOT_PATH / Path("source")
EPISODES_FILE = SOURCE_PATH / "Episodes.csv"
OUTPUT_PATH = ROOT_PATH / Path("mediainfo")
FRAME_PATH = ROOT_PATH / Path("frames")

def read_frames(episode: EpisodeInfo):
    """
    Uses ffmpeg configured to burn in subtitles to make
    a generator for each frame in the source file
    """
    container = av.open(str(episode.file_path))
    container.streams.video[0].thread_type = "AUTO"
    graph = Graph()

    in_video = graph.add_buffer(template=container.streams.video[0])
    subs = graph.add("subtitles", filename=str(episode.file_path), si="0")
    sink = graph.add("buffersink")

    in_video.link_to(subs)
    subs.link_to(sink)
    graph.configure()

    for frame in container.decode(container.streams.video[0]):
        graph.push(frame)
        pulled = graph.pull()
        yield (pulled.time, pulled)

def ms_to_hhmmssff(time_ms, main_sep=':', frac_sep='.'):
    """
    Converts from ms to h:mm:ss.ff format
    """
    fraction = int((time_ms % 1000) / 10)
    seconds = int((time_ms / 1000) % 60)
    minutes = int((time_ms / (1000 * 60)) % 60)
    hours = int((time_ms / (1000 * 60 * 60)))

    return f"{hours}{main_sep}{minutes:02}{main_sep}{seconds:02}{frac_sep}{fraction:02}"

def extract_subtitles(episode: EpisodeInfo, subtitles: List[SubtitleLine]):
    """
    Enumerates through the provided list of subtitles, while at the same time
    enumerating through the video frames provided by read_frames. When a subtitle
    is on the screen, save out the frame.
    """
    base_frame_name = f"{episode_info.overall_order:03}_{episode_info.series_order:02}_{episode_info.series_name}_{episode_info.episode_number:02}"
    frame_dir = FRAME_PATH / base_frame_name
    frame_dir.mkdir(parents=True, exist_ok=True)

    frame_info_path = frame_dir / "frame_info.json"

    if frame_info_path.exists():
        print(f"Skipping {episode.file_path}")
        return

    sub_times = sorted((((((sub.start_ms + sub.end_ms) / 2) / 1000), sub) for sub in subtitles), key=lambda t: t[0])

    frames = read_frames(episode)
    extracted: list[ExtractedFrame] = []
    for sub_time, sub in sub_times:
        for frame_time, frame in frames:
            if frame_time >= sub_time:
                frame_name = f"{base_frame_name}_{ms_to_hhmmssff(sub_time * 1000,'_','_')}.jpg"
                frame_path = frame_dir / frame_name
                frame.to_image().save(frame_path)
                print(f"{episode.series_name} {episode.episode_number:02} - {ms_to_hhmmssff(sub.start_ms)} -> {frame_name}:\n {sub.text} ")
                extracted.append(ExtractedFrame(
                    episode.series_order,
                    episode.series_name,
                    episode.episode_number,
                    episode.overall_order,
                    sub.start,
                    sub.start_ms,
                    sub.end,
                    sub.end_ms,
                    ms_to_hhmmssff(frame_time * 1000),
                    frame_time* 1000,
                    sub.text,
                    f"{base_frame_name}/{frame_name}"
                ))
                break
    print(f"{episode.series_name} {episode.episode_number:02} - Completed")
    with open(frame_info_path, "w", encoding="utf8") as frame_info_file:
        json.dump([asdict(e) for e in extracted], frame_info_file, indent=2)

for episode_info_filename in glob.glob(path.join(OUTPUT_PATH, "**", "episode_info.json")):
    base_path = Path(episode_info_filename).parent

    with open(episode_info_filename, "r", encoding="utf8") as episode_info_file:
        episode_info = EpisodeInfo.from_json_dict(json.load(episode_info_file))

    with open(base_path / 'subs.json', "r", encoding="utf8") as subs_file:
        sub_info = json.load(subs_file)

    if len(sub_info) == 1:
        sub_track_info = sub_info[0]
    else:
        sub_track_info = next(
            (t for t in sub_info if t['info']['properties']['default_track']),
            sub_info[0])
    print(base_path)
    sub_path = Path(sub_track_info['file_name']).parent / f"{sub_track_info['track']}_{sub_track_info['language']}.json"

    with open(sub_path, "r", encoding="utf8") as sub_file:
        json_subs = json.load(sub_file)
        sub_lines = [SubtitleLine.from_json_dict(l) for l in json_subs['subs']]

    extract_subtitles(episode_info, sub_lines)
    