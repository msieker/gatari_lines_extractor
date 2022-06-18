"""
Looks for frame_info.json files, and then emits an HTML file in the same
path that contains the frame that was extracted, along with some basic information
"""
from os import path
import glob
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

SUB_VERSION = 1
ROOT_PATH = Path("/mnt/e/gatari_lines")
SOURCE_PATH = ROOT_PATH / Path("source")
EPISODES_FILE = SOURCE_PATH / "Episodes.csv"
OUTPUT_PATH = ROOT_PATH / Path("mediainfo")
FRAME_PATH = ROOT_PATH / Path("frames")

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)
template = env.get_template("episode_preview.jinja")

def ms_to_hhmmssff(time_ms, main_sep=':', frac_sep='.'):
    """
    Converts from ms to h:mm:ss.ff format
    """
    fraction = int((time_ms % 1000) / 10)
    seconds = int((time_ms / 1000) % 60)
    minutes = int((time_ms / (1000 * 60)) % 60)
    hours = int((time_ms / (1000 * 60 * 60)))

    return f"{hours}{main_sep}{minutes:02}{main_sep}{seconds:02}{frac_sep}{fraction:02}"

for frameinfo_filename in glob.glob(path.join(FRAME_PATH, "**", "frame_info.json")):
    frames = json.load(open(frameinfo_filename, 'r', encoding='utf8'))
    with open(Path(frameinfo_filename).parent / 'preview.html','w', encoding='utf8') as f:
        f.write(template.render(frames=[{
            "path": f['frame_path'].split('/')[1],
            "sub": f['start'],
            "extracted": f["extracted"],
            "target": ms_to_hhmmssff((f["start_ms"]+f["end_ms"])/2),
            "text": f['text'].replace('\n','<br>')
        } for f in frames]))
    