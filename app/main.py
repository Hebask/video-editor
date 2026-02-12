from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="AI Video Highlighter")
app.include_router(router)
