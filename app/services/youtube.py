from pathlib import Path
import yt_dlp

def download_youtube_video(url: str, out_dir: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "outtmpl": str(Path(out_dir) / "%(title)s.%(ext)s"),
        "format": "mp4/bestvideo+bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        final_path = Path(filename)
        if final_path.suffix.lower() != ".mp4":
            mp4_guess = final_path.with_suffix(".mp4")
            if mp4_guess.exists():
                return str(mp4_guess)
        return str(final_path)
