import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.models.schemas import (
    FeatureMeasurement,
    FileInfoResponse,
    FileMeasurementsResponse,
    FileStatus,
    MeasurementDetail,
)

class FileRepository:
    """
    SQLite persistence layer for file metadata, extracted features,
    and geometric measurement results.
    """

    def __init__(self, db_path: Path = settings.DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    feature_count INTEGER DEFAULT 0,
                    crs TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    file_size_bytes INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    feature_id TEXT NOT NULL,
                    geometry_type TEXT NOT NULL,
                    original_crs TEXT NOT NULL,
                    projected_crs TEXT,
                    is_supported INTEGER NOT NULL,
                    measurements_json TEXT,
                    properties_json TEXT,
                    geometry_json TEXT,
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_features_file_id ON features (file_id)"
            )
            conn.commit()

    def save_file(self, file_info: FileInfoResponse) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files (
                    id, filename, file_type, feature_count, crs,
                    status, error_message, file_size_bytes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_info.id,
                    file_info.filename,
                    file_info.file_type,
                    file_info.feature_count,
                    file_info.crs,
                    file_info.status.value,
                    file_info.error_message,
                    file_info.file_size_bytes,
                    file_info.created_at.isoformat(),
                ),
            )
            conn.commit()

    def update_file_status(
        self,
        file_id: str,
        status: FileStatus,
        feature_count: Optional[int] = None,
        crs: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        with self._get_connection() as conn:
            updates = ["status = ?"]
            params: List[Any] = [status.value]

            if feature_count is not None:
                updates.append("feature_count = ?")
                params.append(feature_count)
            if crs is not None:
                updates.append("crs = ?")
                params.append(crs)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            params.append(file_id)
            query = f"UPDATE files SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()

    def get_file(self, file_id: str) -> Optional[FileInfoResponse]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return FileInfoResponse(
                id=row["id"],
                filename=row["filename"],
                file_type=row["file_type"],
                feature_count=row["feature_count"],
                crs=row["crs"],
                status=FileStatus(row["status"]),
                error_message=row["error_message"],
                file_size_bytes=row["file_size_bytes"],
                created_at=row["created_at"],
            )

    def list_files(self, limit: int = 100, offset: int = 0) -> List[FileInfoResponse]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM files ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cursor.fetchall()
            return [
                FileInfoResponse(
                    id=row["id"],
                    filename=row["filename"],
                    file_type=row["file_type"],
                    feature_count=row["feature_count"],
                    crs=row["crs"],
                    status=FileStatus(row["status"]),
                    error_message=row["error_message"],
                    file_size_bytes=row["file_size_bytes"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def count_files(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM files")
            return cursor.fetchone()["count"]

    def save_features(
        self,
        file_id: str,
        feature_measurements: List[FeatureMeasurement],
        geometries: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        with self._get_connection() as conn:
            data = []
            for idx, fm in enumerate(feature_measurements):
                meas_json = (
                    json.dumps(fm.measurements.model_dump())
                    if fm.measurements
                    else None
                )
                props_json = json.dumps(fm.properties)
                geom_json = (
                    json.dumps(geometries[idx])
                    if geometries and idx < len(geometries)
                    else None
                )

                data.append(
                    (
                        file_id,
                        str(fm.feature_id),
                        fm.geometry_type,
                        fm.original_crs,
                        fm.projected_crs,
                        1 if fm.is_supported else 0,
                        meas_json,
                        props_json,
                        geom_json,
                    )
                )

            conn.executemany(
                """
                INSERT INTO features (
                    file_id, feature_id, geometry_type, original_crs,
                    projected_crs, is_supported, measurements_json,
                    properties_json, geometry_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
            conn.commit()

    def get_measurements_response(self, file_id: str) -> Optional[FileMeasurementsResponse]:
        file_info = self.get_file(file_id)
        if not file_info:
            return None

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM features WHERE file_id = ? ORDER BY id ASC",
                (file_id,),
            )
            rows = cursor.fetchall()

            features: List[FeatureMeasurement] = []
            total_area: float = 0.0
            total_length: float = 0.0
            has_area = False
            has_length = False

            for row in rows:
                meas = None
                if row["measurements_json"]:
                    meas_dict = json.loads(row["measurements_json"])
                    meas = MeasurementDetail(**meas_dict)
                    if meas.area_sq_meters is not None:
                        total_area += meas.area_sq_meters
                        has_area = True
                    if meas.length_meters is not None:
                        total_length += meas.length_meters
                        has_length = True

                props = json.loads(row["properties_json"]) if row["properties_json"] else {}

                features.append(
                    FeatureMeasurement(
                        feature_id=row["feature_id"],
                        geometry_type=row["geometry_type"],
                        original_crs=row["original_crs"],
                        projected_crs=row["projected_crs"],
                        is_supported=bool(row["is_supported"]),
                        measurements=meas,
                        properties=props,
                    )
                )

            return FileMeasurementsResponse(
                id=file_info.id,
                filename=file_info.filename,
                feature_count=file_info.feature_count,
                crs=file_info.crs,
                status=file_info.status,
                total_area_sq_meters=round(total_area, 4) if has_area else None,
                total_length_meters=round(total_length, 4) if has_length else None,
                features=features,
            )

    def get_feature_geometries(self, file_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT feature_id, geometry_type, geometry_json, properties_json, original_crs FROM features WHERE file_id = ?",
                (file_id,),
            )
            results = []
            for row in cursor.fetchall():
                geom = json.loads(row["geometry_json"]) if row["geometry_json"] else None
                props = json.loads(row["properties_json"]) if row["properties_json"] else {}
                results.append(
                    {
                        "type": "Feature",
                        "id": row["feature_id"],
                        "geometry": geom,
                        "properties": {
                            **props,
                            "original_crs": row["original_crs"],
                            "geometry_type": row["geometry_type"],
                        },
                    }
                )
            return results

    def delete_file(self, file_id: str) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM features WHERE file_id = ?", (file_id,))
            cursor = conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
            return cursor.rowcount > 0

file_repository = FileRepository()
