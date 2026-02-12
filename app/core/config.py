from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    storage_dir: str = "storage"
    uploads_dir: str = "storage/uploads"
    jobs_dir: str = "storage/jobs"
    max_upload_mb: int = 500

settings = Settings()
