from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, HttpUrl
from pathlib import Path

from app.core.config import settings
from app.services.storage import ensure_dirs, new_job_id, job_dir, save_upload
from app.services.youtube import download_youtube_video

from app.services.media import extract_audio
from app.services.transcribe import transcribe_audio
import json
from app.services.highlight import select_highlights

from app.services.render import render_highlights


router = APIRouter()

class YoutubeRequest(BaseModel):
    url: HttpUrl

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/video/upload")
async def upload_video(file: UploadFile = File(...)):
    ensure_dirs(settings.uploads_dir, settings.jobs_dir)

    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".mov", ".mkv", ".webm"]:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    content = await file.read()
    job_id = new_job_id()
    jd = job_dir(settings.jobs_dir, job_id)

    video_path = save_upload(jd, f"input{ext}", content)

    return {
        "job_id": job_id,
        "source": "upload",
        "video_path": video_path,
        "next": "POST /jobs/{job_id}/transcribe (Phase 2)"
    }

@router.post("/video/youtube")
def youtube_to_job(payload: YoutubeRequest):
    ensure_dirs(settings.uploads_dir, settings.jobs_dir)

    job_id = new_job_id()
    jd = job_dir(settings.jobs_dir, job_id)

    video_path = download_youtube_video(str(payload.url), jd)

    if not Path(video_path).exists():
        raise HTTPException(status_code=500, detail="YouTube download failed")

    return {
        "job_id": job_id,
        "source": "youtube",
        "video_path": video_path,
        "next": "POST /jobs/{job_id}/transcribe (Phase 2)"
    }

@router.post("/jobs/{job_id}/transcribe")
def transcribe_job(job_id: str):
    jd = Path(settings.jobs_dir) / job_id

    if not jd.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    video_files = list(jd.glob("input.*")) + list(jd.glob("*.mp4"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(video_files[0])

    audio_path = extract_audio(video_path, str(jd))

    result = transcribe_audio(audio_path, str(jd))

    return {
        "job_id": job_id,
        "message": "Transcription complete",
        "segments_count": len(result.get("segments", []))
    }

@router.post("/jobs/{job_id}/highlights")
def make_highlights(job_id: str, target_seconds: float = 60.0):
    jd = Path(settings.jobs_dir) / job_id
    transcript_path = jd / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="transcript.json not found. Run /transcribe first.")

    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    highlights = select_highlights(segments, target_seconds=target_seconds)

    out_path = jd / "highlights.json"
    out_path.write_text(json.dumps(highlights, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "job_id": job_id,
        "target_seconds": target_seconds,
        "highlights_count": len(highlights),
        "highlights_path": str(out_path),
        "highlights_preview": highlights[:3],
        "next": "Phase 4: /jobs/{job_id}/render (trim + merge)"
    }

@router.post("/jobs/{job_id}/render")
def render_job(job_id: str):
    jd = Path(settings.jobs_dir) / job_id

    if not jd.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    video_files = list(jd.glob("input.*")) + list(jd.glob("*.mp4"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Video not found")

    video_path = str(video_files[0])

    highlights_path = jd / "highlights.json"
    if not highlights_path.exists():
        raise HTTPException(status_code=404, detail="highlights.json not found. Run /highlights first.")

    import json
    highlights = json.loads(highlights_path.read_text(encoding="utf-8"))

    final_video = render_highlights(video_path, highlights, str(jd))

    return {
        "job_id": job_id,
        "message": "Render complete",
        "final_video_path": final_video
    }
