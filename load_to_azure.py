"""
Takes data from all frame_info.json files in a directory, and loads
them into an Azure table.
"""
from os import path, environ
import glob
import json
from pathlib import Path
from typing import List

from azure.data.tables import TableClient
from tqdm import tqdm

from models import ExtractedFrame

ROOT_PATH = Path("/mnt/e/gatari_lines")
FRAME_PATH = ROOT_PATH / Path("frames")

all_frames: List[ExtractedFrame] = []

azure_table_url = environ.get('AZURE_TABLE_URL')
if not azure_table_url:
    print('The AZURE_TABLE_URL needs to be set before running this')
    exit()

table_client = TableClient.from_table_url(azure_table_url)
for frameinfo_filename in glob.glob(path.join(FRAME_PATH, "**", "frame_info.json")):
    frames = [ExtractedFrame.from_json_dict(l) for l in json.load(open(frameinfo_filename, 'r', encoding="utf8"))]
    all_frames += frames

all_frames = sorted(all_frames, key=lambda f: (f.overall_order, f.extracted_ms))

output = [{
    'PartitionKey': f"{f.overall_order:03}_{f.series_order:02}_{f.series_name}_{f.episode_number:02}",
    'RowKey': f.start.replace(':','_').replace('.','_'),
    'Order': f.overall_order,
    'Series': f.series_name,
    'Episode': f.episode_number,
    'Frame': 'frames/' + f.frame_path,
    'Lines': f.text,
    'Time': f.extracted,
    'Time_ms':  f.extracted_ms,
    'NextPartitionKey': '',
    'NextRowKey': '',
} for f in all_frames]

for i, f in enumerate(output[:-1]):
    f['NextPartitionKey'] = output[i+1]['PartitionKey']
    f['NextRowKey'] = output[i+1]['RowKey']

output[-1]['NextPartitionKey'] = output[0]['PartitionKey']
output[-1]['NextRowKey'] = output[0]['RowKey']

line_count = len(output)

with tqdm(total=len(output)) as t:
    for l in output:
        t.set_description(f"{l['Series']} {l['Episode']:02} {l['Time']}")
        table_client.create_entity(l)
        t.update()
