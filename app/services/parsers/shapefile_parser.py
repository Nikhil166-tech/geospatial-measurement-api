import datetime
import logging
from pathlib import Path
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import zipfile
import shapefile
from shapely.geometry import shape as to_shapely_shape
from app.core.exceptions import FileProcessingException, InvalidFileFormatException
from app.services.crs_service import crs_service
from app.services.parsers.base import BaseGeospatialParser, ParsedFeature

logger = logging.getLogger(__name__)

class ShapefileParser(BaseGeospatialParser):
    """
    Parser for zipped ESRI Shapefile packages (.shp, .shx, .dbf, .prj).
    Handles safe extraction, CRS detection from .prj, and feature extraction.
    """

    def parse(self, file_path: Path) -> Tuple[str, List[ParsedFeature]]:
        if not file_path.exists():
            raise FileProcessingException(f"Zip file not found at {file_path}")

        if not zipfile.is_zipfile(file_path):
            raise InvalidFileFormatException("Uploaded file is not a valid ZIP archive.")

        temp_dir = Path(tempfile.mkdtemp(prefix="shp_extract_"))

        try:
            # 1. Safely extract zip files (prevent zip-slip)
            with zipfile.ZipFile(file_path, "r") as archive:
                for member in archive.infolist():
                    target_path = (temp_dir / member.filename).resolve()
                    if not str(target_path).startswith(str(temp_dir.resolve())):
                        raise InvalidFileFormatException("Zip archive contains unsafe paths.")
                archive.extractall(temp_dir)

            # 2. Locate .shp file
            shp_files = list(temp_dir.rglob("*.shp"))
            if not shp_files:
                raise InvalidFileFormatException(
                    "Zip archive must contain at least one .shp Shapefile."
                )

            shp_path = shp_files[0]
            base_stem = shp_path.stem
            parent_dir = shp_path.parent

            # 3. Detect CRS from companion .prj file
            prj_path = parent_dir / f"{base_stem}.prj"
            crs_str = "EPSG:4326"

            if prj_path.exists():
                try:
                    prj_text = prj_path.read_text(encoding="utf-8", errors="ignore").strip()
                    if prj_text:
                        _, crs_str = crs_service.parse_crs(prj_text)
                except Exception as e:
                    logger.warning(f"Error reading .prj file: {e}. Defaulting to EPSG:4326.")

            # 4. Read shapes and records with pyshp
            features: List[ParsedFeature] = []
            with shapefile.Reader(str(shp_path)) as sf:
                for idx, shape_rec in enumerate(sf.shapeRecords()):
                    # Sanitize attributes to make them JSON-safe
                    raw_props = shape_rec.record.as_dict()
                    sanitized_props: Dict[str, Any] = {}
                    for k, v in raw_props.items():
                        if isinstance(v, (datetime.date, datetime.datetime)):
                            sanitized_props[k] = v.isoformat()
                        elif isinstance(v, bytes):
                            sanitized_props[k] = v.decode("utf-8", errors="replace")
                        else:
                            sanitized_props[k] = v

                    # Extract geometry
                    geom = None
                    geom_type = "Unknown"

                    try:
                        geo_interface = shape_rec.shape.__geo_interface__
                        if geo_interface and geo_interface.get("coordinates"):
                            geom = to_shapely_shape(geo_interface)
                            geom_type = geom.geom_type
                        else:
                            geom_type = "NullShape"
                    except Exception as ge:
                        logger.warning(f"Failed to parse geometry for feature {idx}: {ge}")
                        geom_type = "MalformedGeometry"

                    features.append(
                        ParsedFeature(
                            feature_id=idx,
                            geometry_type=geom_type,
                            geometry=geom,
                            properties=sanitized_props,
                            crs=crs_str,
                        )
                    )

            return crs_str, features

        finally:
            # Clean up extracted temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

shapefile_parser = ShapefileParser()
