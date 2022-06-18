"""
Common dataclasses shared between multiple scripts
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Dict, Tuple

@dataclass
class EpisodeInfo:
    """
    Contains info for one episode read from the source file
    """
    file_name: Annotated[str, "Base file name of episode, read from source file"]
    series_order: Annotated[int, "Overall order of this series within the work"]
    series_name: Annotated[str, "The name of the series for this episode"]
    episode_number: Annotated[int, "The number of the episode within the work"]
    overall_order: Annotated[int, "The number of the episode within the overall work"]
    file_path: Annotated[Path, "Full path of the media file for this episode"]
    episode_path: Annotated[Path, "Directory containing the exported artifacts for this episode"]

    def as_json_dict(self):
        """
        Returns a dictionary that can be turned into json
        """
        return {
            "file_name": self.file_name,
            "series_order": self.series_order,
            "series_name": self.series_name,
            "episode_number": self.episode_number,
            "overall_order": self.overall_order,
            "file_path": str(self.file_path),
            "episode_path": str(self.episode_path)
        }

    @classmethod
    def from_json_dict(cls, json_dict: Dict):
        """
        Creates an instance of EpisodeInfo from a JSON dictionary
        """
        return EpisodeInfo(
            file_name=json_dict['file_name'],
            series_order=json_dict['series_order'],
            series_name=json_dict['series_name'],
            episode_number=json_dict['episode_number'],
            overall_order=json_dict['overall_order'],
            file_path=Path(json_dict['file_path']),
            episode_path=Path(json_dict['episode_path'])
        )

@dataclass(frozen=True)
class SubtitleLine:
    """
    Stores info for an individual subtitle line
    """
    start: Annotated[str, "Timestamp of when this subtitle is displayed"]
    start_ms: Annotated[int, "Time in milliseconds of when this subtitle is displayed"]
    end: Annotated[str, "Timestamp of when this subtitle is hidden"]
    end_ms: Annotated[int, "Time in milliseconds of when this subtitle is hidden"]
    raw_subs: Annotated[Tuple[str,...], "Raw subtitle text for this line, including control characters"]
    text: Annotated[str, "Text only version of subtitle"]

    @classmethod
    def from_json_dict(cls, json_dict: Dict):
        """
        Creates an instance of SubtitleLine from a JSON dictionary
        """
        return SubtitleLine(
            start=json_dict['start'],
            start_ms=json_dict['start_ms'],
            end=json_dict['end'],
            end_ms=json_dict['end_ms'],
            raw_subs=tuple(json_dict['raw_subs']),
            text=json_dict['text'],
        )

@dataclass
class ExtractedFrame:
    """
    Stores information about an extracted frame
    """
    series_order: Annotated[int, "Overall order of this series within the work"]
    series_name: Annotated[str, "The name of the series for this episode"]
    episode_number: Annotated[int, "The number of the episode within the work"]
    overall_order: Annotated[int, "The number of the episode within the overall work"]
    start: Annotated[str, "Timestamp of when this subtitle is displayed"]
    start_ms: Annotated[int, "Time in milliseconds of when this subtitle is displayed"]
    end: Annotated[str, "Timestamp of when this subtitle is hidden"]
    end_ms: Annotated[int, "Time in milliseconds of when this subtitle is hidden"]
    extracted: Annotated[str, "Timestamp of when this frame was extracted"]
    extracted_ms: Annotated[int, "Time in milliseconds of when this frame was extracted"]
    text: Annotated[str, "Text only version of subtitle"]
    frame_path: Annotated[str, "The relative path of the frame to the subtitle output directory"]

    @classmethod
    def from_json_dict(cls, json_dict: Dict):
        """
        Creates an instance of ExtractedFrame from a JSON dict
        """
        return ExtractedFrame(
            json_dict["series_order"],
            json_dict["series_name"],
            json_dict["episode_number"],
            json_dict["overall_order"],
            json_dict["start"],
            json_dict["start_ms"],
            json_dict["end"],
            json_dict["end_ms"],
            json_dict["extracted"],
            json_dict["extracted_ms"],
            json_dict["text"],
            json_dict["frame_path"],
        )
