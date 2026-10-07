from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
from typing import Dict, List, Optional
import uuid
from fastapi import UploadFile
from shapely.geometry import mapping
from app.core.config import settings
from app.core.exceptions import (
    FileProcessingException,
    InvalidFileFormatException,
    ResourceNotFoundException,
)
from app.models.schemas import (
    FeatureMeasurement,
    FileInfoResponse,
    FileMeasurementsResponse,
    FileStatus,
)
from app.services.measurement_service import measurement_service
from app.services.parsers.kml_parser import kml_parser
from app.services.parsers.shapefile_parser import shapefile_parser
from app.storage.repository import file_repository

logger = logging.getLogger(__name__)

class FileService:
    """
    Coordinates file uploading, parsing, CRS handling,
    measurement computation, and database persistence.
    """

    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.repo = file_repository

    async def process_uploaded_file(self, file: UploadFile) -> FileInfoResponse:
        """
        Saves uploaded file to disk, parses geospatial contents,
        reprojects to appropriate projected CRS, and calculates measurements.
        """
        filename = file.filename or "uploaded_file"
        file_ext = Path(filename).suffix.lower()

        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise InvalidFileFormatException(
                f"Unsupported file extension '{file_ext}'. Allowed formats: .kml, .zip (Shapefile archive)."
            )

        file_type = "kml" if file_ext == ".kml" else "shapefile"
        file_id = uuid.uuid4().hex[:8]
        saved_file_path = self.upload_dir / f"{file_id}_{filename}"

        # 1. Stream file to disk while checking file size
        total_bytes = 0
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        try:
            with open(saved_file_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise InvalidFileFormatException(
                            f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB}MB."
                        )
                    buffer.write(chunk)
        except Exception as e:
            if saved_file_path.exists():
                saved_file_path.unlink()
            if isinstance(e, InvalidFileFormatException):
                raise e
            raise FileProcessingException(f"Failed to save file: {str(e)}")

        # 2. Record initial file metadata
        file_info = FileInfoResponse(
            id=file_id,
            filename=filename,
            file_type=file_type,
            feature_count=0,
            crs="UNKNOWN",
            status=FileStatus.PROCESSING,
            error_message=None,
            file_size_bytes=total_bytes,
            created_at=datetime.now(timezone.utc),
        )
        self.repo.save_file(file_info)

        # 3. Parse and compute measurements
        try:
            if file_type == "kml":
                base_crs, parsed_features = kml_parser.parse(saved_file_path)
            else:
                base_crs, parsed_features = shapefile_parser.parse(saved_file_path)

            feature_measurements: List[FeatureMeasurement] = []
            geometries_json: List[Optional[Dict]] = []

            for pf in parsed_features:
                fm = measurement_service.process_feature(
                    feature_id=pf.feature_id,
                    geometry=pf.geometry,
                    source_crs_str=pf.crs or base_crs,
                    properties=pf.properties,
                )
                feature_measurements.append(fm)

                # Store GeoJSON geometry mapping
                geom_map = mapping(pf.geometry) if pf.geometry and not pf.geometry.is_empty else None
                geometries_json.append(geom_map)

            # 4. Save features & update file status
            self.repo.save_features(file_id, feature_measurements, geometries_json)
            self.repo.update_file_status(
                file_id=file_id,
                status=FileStatus.COMPLETED,
                feature_count=len(feature_measurements),
                crs=base_crs,
            )

            file_info.status = FileStatus.COMPLETED
            file_info.feature_count = len(feature_measurements)
            file_info.crs = base_crs
            return file_info

        except Exception as e:
            logger.error(f"Failed processing file {file_id}: {e}", exc_info=True)
            err_msg = str(e)
            self.repo.update_file_status(
                file_id=file_id,
                status=FileStatus.FAILED,
                error_message=err_msg,
            )
            file_info.status = FileStatus.FAILED
            file_info.error_message = err_msg
            if isinstance(e, (InvalidFileFormatException, FileProcessingException)):
                raise e
            raise FileProcessingException(f"Failed processing file: {err_msg}")

    def get_file_info(self, file_id: str) -> FileInfoResponse:
        file_info = self.repo.get_file(file_id)
        if not file_info:
            raise ResourceNotFoundException(f"File with id '{file_id}' not found.")
        return file_info

    def get_file_measurements(self, file_id: str) -> FileMeasurementsResponse:
        meas_resp = self.repo.get_measurements_response(file_id)
        if not meas_resp:
            raise ResourceNotFoundException(f"File with id '{file_id}' not found.")
        return meas_resp

    def get_file_features_geojson(self, file_id: str) -> Dict:
        file_info = self.get_file_info(file_id)
        features = self.repo.get_feature_geometries(file_id)
        return {
            "type": "FeatureCollection",
            "file_id": file_info.id,
            "filename": file_info.filename,
            "crs": file_info.crs,
            "features": features,
        }

    def list_files(self, limit: int = 50, offset: int = 0):
        total = self.repo.count_files()
        files = self.repo.list_files(limit, offset)
        return {"total": total, "files": files}

    def delete_file(self, file_id: str) -> bool:
        file_info = self.repo.get_file(file_id)
        if not file_info:
            raise ResourceNotFoundException(f"File with id '{file_id}' not found.")

        # Remove file from disk if present
        for f in self.upload_dir.glob(f"{file_id}_*"):
            try:
                f.unlink()
            except Exception:
                pass

        return self.repo.delete_file(file_id)

file_service = FileService()
