import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = BASE_DIR / "geospatial.db"

class Settings(BaseModel):
    APP_NAME: str = "Geospatial File Measurement API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    UPLOAD_DIR: Path = UPLOADS_DIR
    DATABASE_PATH: Path = DB_PATH
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: set = {".kml", ".zip"}

settings = Settings()
