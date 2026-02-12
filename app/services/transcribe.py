from pathlib import Path
import json
from faster_whisper import WhisperModel

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel("large", device="cuda", compute_type="float16")
    return _model

def transcribe_audio(audio_path: str, job_dir: str) -> dict:
    model = _get_model()

    segments, info = model.transcribe(audio_path, vad_filter=True)

    segs = []
    full_text = []
    for s in segments:
        text = (s.text or "").strip()
        if not text:
            continue
        segs.append({"start": float(s.start), "end": float(s.end), "text": text})
        full_text.append(text)

    result = {
        "text": " ".join(full_text).strip(),
        "segments": segs,
        "language": getattr(info, "language", None),
        "duration": getattr(info, "duration", None),
    }

    transcript_path = Path(job_dir) / "transcript.json"
    transcript_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
