import subprocess
from pathlib import Path

def extract_audio(video_path: str, output_path: str) -> str:
    output_file = Path(output_path) / "audio.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_file)
    ]

    subprocess.run(cmd, check=True)

    return str(output_file)
