import logging
from typing import Any, Dict, Optional, Tuple, Union
from pyproj import CRS
from shapely.geometry import (
    Point,
    MultiPoint,
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    GeometryCollection,
)
from shapely.geometry.base import BaseGeometry
from shapely.geometry import mapping
from app.models.schemas import FeatureMeasurement, MeasurementDetail
from app.services.crs_service import crs_service

logger = logging.getLogger(__name__)

class MeasurementService:
    """
    Calculates metric measurements (area, length, perimeter) for geospatial geometries
    by projecting geographic coordinates to appropriate metric planar reference systems.
    """

    def process_feature(
        self,
        feature_id: Union[int, str],
        geometry: BaseGeometry,
        source_crs_str: str,
        properties: Dict[str, Any],
    ) -> FeatureMeasurement:
        """
        Takes a geometry and attributes, reprojects if necessary,
        and calculates measurements according to geometric type.
        """
        source_crs_obj, clean_source_crs = crs_service.parse_crs(source_crs_str)
        geom_type = geometry.geom_type if geometry else "Unknown"

        if geometry is None or geometry.is_empty:
            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                original_crs=clean_source_crs,
                projected_crs=None,
                is_supported=False,
                measurements=MeasurementDetail(
                    notes="Geometry is null or empty. No measurement calculated."
                ),
                properties=properties,
            )

        # 1. Point / MultiPoint - explicit requirement: No measurement required
        if isinstance(geometry, (Point, MultiPoint)):
            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                original_crs=clean_source_crs,
                projected_crs=None,
                is_supported=True,
                measurements=MeasurementDetail(
                    area_sq_meters=None,
                    length_meters=None,
                    notes="Point geometry does not have length or area.",
                ),
                properties=properties,
            )

        # 2. Polygon / MultiPolygon - calculate Area
        elif isinstance(geometry, (Polygon, MultiPolygon)):
            projected_geom, target_crs_name = crs_service.project_geometry(
                geometry, source_crs_obj
            )
            area_sq_m = round(float(projected_geom.area), 4)
            perimeter_m = round(float(projected_geom.length), 4)
            area_ha = round(area_sq_m / 10000.0, 6)
            area_sq_km = round(area_sq_m / 1_000_000.0, 8)

            notes = f"Calculated using projected planar coordinates ({target_crs_name})."
            if clean_source_crs == "EPSG:4326":
                # Supplementary geodesic comparison for documentation integrity
                geodesic_area = crs_service.compute_geodesic_polygon_area(geometry)
                notes += f" Geodesic WGS84 area: {round(geodesic_area, 2)} m²."

            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                original_crs=clean_source_crs,
                projected_crs=target_crs_name,
                is_supported=True,
                measurements=MeasurementDetail(
                    area_sq_meters=area_sq_m,
                    area_hectares=area_ha,
                    area_sq_km=area_sq_km,
                    perimeter_meters=perimeter_m,
                    notes=notes,
                ),
                properties=properties,
            )

        # 3. LineString / MultiLineString - calculate Length
        elif isinstance(geometry, (LineString, MultiLineString)):
            projected_geom, target_crs_name = crs_service.project_geometry(
                geometry, source_crs_obj
            )
            length_m = round(float(projected_geom.length), 4)
            length_km = round(length_m / 1000.0, 6)

            notes = f"Calculated using projected planar coordinates ({target_crs_name})."
            if clean_source_crs == "EPSG:4326":
                geodesic_len = crs_service.compute_geodesic_linestring_length(geometry)
                notes += f" Geodesic WGS84 length: {round(geodesic_len, 2)} m."

            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                original_crs=clean_source_crs,
                projected_crs=target_crs_name,
                is_supported=True,
                measurements=MeasurementDetail(
                    length_meters=length_m,
                    length_km=length_km,
                    notes=notes,
                ),
                properties=properties,
            )

        # 4. GeometryCollection - graceful composition
        elif isinstance(geometry, GeometryCollection):
            projected_geom, target_crs_name = crs_service.project_geometry(
                geometry, source_crs_obj
            )
            total_area = round(float(projected_geom.area), 4)
            total_len = round(float(projected_geom.length), 4)

            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                original_crs=clean_source_crs,
                projected_crs=target_crs_name,
                is_supported=True,
                measurements=MeasurementDetail(
                    area_sq_meters=total_area if total_area > 0 else None,
                    length_meters=total_len if total_len > 0 else None,
                    notes=f"Composite geometry evaluated via {target_crs_name}.",
                ),
                properties=properties,
            )

        # 5. Unsupported Geometry Type - handled gracefully
        else:
            return FeatureMeasurement(
                feature_id=feature_id,
                geometry_type=geom_type,
                original_crs=clean_source_crs,
                projected_crs=None,
                is_supported=False,
                measurements=MeasurementDetail(
                    notes=f"Geometry type '{geom_type}' is not supported for measurement calculation."
                ),
                properties=properties,
            )

measurement_service = MeasurementService()
