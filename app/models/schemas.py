from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class FileStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class GeometryTypeEnum(str, Enum):
    POINT = "Point"
    LINESTRING = "LineString"
    POLYGON = "Polygon"
    MULTIPOINT = "MultiPoint"
    MULTILINESTRING = "MultiLineString"
    MULTIPOLYGON = "MultiPolygon"
    GEOMETRYCOLLECTION = "GeometryCollection"
    UNKNOWN = "Unknown"

class MeasurementDetail(BaseModel):
    area_sq_meters: Optional[float] = Field(None, description="Calculated area in square meters (m²)")
    area_hectares: Optional[float] = Field(None, description="Calculated area in hectares (ha)")
    area_sq_km: Optional[float] = Field(None, description="Calculated area in square kilometers (km²)")
    length_meters: Optional[float] = Field(None, description="Calculated length or perimeter in meters (m)")
    length_km: Optional[float] = Field(None, description="Calculated length in kilometers (km)")
    perimeter_meters: Optional[float] = Field(None, description="Calculated perimeter for polygons in meters (m)")
    notes: Optional[str] = Field(None, description="Explanatory notes regarding measurement or geometry handling")

class FeatureMeasurement(BaseModel):
    feature_id: Union[int, str] = Field(..., description="Unique index or identifier of the feature")
    geometry_type: str = Field(..., description="Type of geometry (e.g. Polygon, LineString, Point)")
    original_crs: str = Field(..., description="Original CRS of the uploaded file")
    projected_crs: Optional[str] = Field(None, description="Projected metric CRS used for accurate measurement")
    is_supported: bool = Field(..., description="Whether this geometry type supports metric measurement")
    measurements: Optional[MeasurementDetail] = Field(None, description="Computed measurement values")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Attributes and properties of the feature")

class RawFeature(BaseModel):
    feature_id: Union[int, str]
    geometry_type: str
    geometry: Dict[str, Any]
    crs: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class FileInfoResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for the uploaded file")
    filename: str = Field(..., description="Original name of the uploaded file")
    file_type: str = Field(..., description="Detected format: kml or shapefile")
    feature_count: int = Field(..., description="Total number of geospatial features extracted")
    crs: str = Field(..., description="Detected Coordinate Reference System")
    status: FileStatus = Field(..., description="Processing status of the file")
    error_message: Optional[str] = Field(None, description="Details if processing failed")
    file_size_bytes: int = Field(..., description="Size of the uploaded file in bytes")
    created_at: datetime = Field(..., description="Timestamp when file was uploaded")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "abc123",
                "filename": "survey.kml",
                "file_type": "kml",
                "feature_count": 120,
                "crs": "EPSG:4326",
                "status": "COMPLETED",
                "error_message": None,
                "file_size_bytes": 1048576,
                "created_at": "2026-10-07T12:00:00"
            }
        }
    }

class FileMeasurementsResponse(BaseModel):
    id: str = Field(..., description="Unique file ID")
    filename: str = Field(..., description="Original filename")
    feature_count: int = Field(..., description="Total features in file")
    crs: str = Field(..., description="Base Coordinate Reference System")
    status: FileStatus = Field(..., description="Processing status")
    total_area_sq_meters: Optional[float] = Field(None, description="Aggregate area of all polygons in m²")
    total_length_meters: Optional[float] = Field(None, description="Aggregate length of all line strings in meters")
    features: List[FeatureMeasurement] = Field(default_factory=list, description="Measurements per feature")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "abc123",
                "filename": "survey.kml",
                "feature_count": 2,
                "crs": "EPSG:4326",
                "status": "COMPLETED",
                "total_area_sq_meters": 15420.50,
                "total_length_meters": 320.15,
                "features": [
                    {
                        "feature_id": 0,
                        "geometry_type": "Polygon",
                        "original_crs": "EPSG:4326",
                        "projected_crs": "EPSG:32643",
                        "is_supported": True,
                        "measurements": {
                            "area_sq_meters": 15420.50,
                            "area_hectares": 1.542,
                            "area_sq_km": 0.01542,
                            "perimeter_meters": 520.4,
                            "notes": "Projected using local UTM Zone 43N"
                        },
                        "properties": {"name": "Field A"}
                    }
                ]
            }
        }
    }

class FileListResponse(BaseModel):
    total: int
    files: List[FileInfoResponse]
