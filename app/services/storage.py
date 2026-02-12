import os
import uuid
from pathlib import Path

def ensure_dirs(*dirs: str) -> None:
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

def new_job_id() -> str:
    return uuid.uuid4().hex

def job_dir(jobs_root: str, job_id: str) -> str:
    p = Path(jobs_root) / job_id
    p.mkdir(parents=True, exist_ok=True)
    return str(p)

def save_upload(upload_dir: str, filename: str, content: bytes) -> str:
    ensure_dirs(upload_dir)
    safe_name = Path(filename).name 
    out_path = Path(upload_dir) / safe_name
    out_path.write_bytes(content)
    return str(out_path)
