import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app
from app.storage.repository import FileRepository

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    # Set isolated temp test database and upload folder
    temp_dir = tmp_path_factory.mktemp("test_geospatial")
    test_db = temp_dir / "test_geospatial.db"
    test_uploads = temp_dir / "uploads"
    test_uploads.mkdir()

    settings.DATABASE_PATH = test_db
    settings.UPLOAD_DIR = test_uploads

    # Re-init repository with test db path
    test_repo = FileRepository(test_db)
    from app.services.file_service import file_service
    file_service.repo = test_repo
    file_service.upload_dir = test_uploads

    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_kml_path():
    return Path(__file__).resolve().parent.parent / "sample_data" / "sample.kml"

@pytest.fixture
def sample_parcels_zip_path():
    return Path(__file__).resolve().parent.parent / "sample_data" / "parcels.zip"

@pytest.fixture
def sample_flight_paths_zip_path():
    return Path(__file__).resolve().parent.parent / "sample_data" / "flight_paths.zip"
