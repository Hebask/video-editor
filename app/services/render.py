import subprocess
from pathlib import Path
from typing import List, Dict

def cut_segment(video_path: str, start: float, end: float, output_path: str):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-to", str(end),
        "-i", video_path,
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)

def concat_segments(segment_paths: List[str], output_path: str):
    out = Path(output_path).resolve()
    list_file = out.parent / "concat_list.txt"

    with open(list_file, "w", encoding="utf-8") as f:
        for p in segment_paths:
            abs_p = Path(p).resolve().as_posix()
            f.write(f"file '{abs_p}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out)
    ]

    subprocess.run(cmd, check=True)
    list_file.unlink(missing_ok=True)

def render_highlights(
    video_path: str,
    highlights: List[Dict],
    job_dir: str
) -> str:

    segments_dir = Path(job_dir) / "segments"
    segments_dir.mkdir(exist_ok=True)

    segment_paths = []

    for i, seg in enumerate(highlights):
        out_path = segments_dir / f"segment_{i}.mp4"
        cut_segment(video_path, seg["start"], seg["end"], str(out_path))
        segment_paths.append(str(out_path))

    final_output = Path(job_dir) / "final.mp4"
    concat_segments(segment_paths, str(final_output))

    return str(final_output)
