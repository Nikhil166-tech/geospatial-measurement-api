import logging
from typing import Optional, Tuple
import numpy as np
import pyproj
from pyproj import CRS, Transformer, Geod
import shapely
from shapely.geometry.base import BaseGeometry
from app.core.exceptions import CRSTransformationException

logger = logging.getLogger(__name__)

class CRSService:
    """
    Handles coordinate reference system detection, validation,
    and automatic projection selection for planar measurements.
    """

    def __init__(self):
        self._geod = Geod(ellps="WGS84")

    @staticmethod
    def parse_crs(crs_input: Optional[str]) -> Tuple[CRS, str]:
        """
        Parses a CRS string, EPSG code, or WKT representation.
        Defaults to EPSG:4326 if None, empty, or unparseable.
        """
        if not crs_input or crs_input.strip() == "":
            return CRS.from_epsg(4326), "EPSG:4326"

        try:
            crs_obj = CRS.from_user_input(crs_input)
            # Try to get clean EPSG identifier if available
            epsg_code = crs_obj.to_epsg()
            clean_str = f"EPSG:{epsg_code}" if epsg_code else crs_obj.name
            return crs_obj, clean_str
        except Exception as e:
            logger.warning(f"Could not parse CRS '{crs_input}': {e}. Defaulting to EPSG:4326.")
            return CRS.from_epsg(4326), "EPSG:4326"

    @staticmethod
    def determine_optimal_projected_crs(geometry: BaseGeometry, source_crs: CRS) -> Tuple[CRS, str]:
        """
        Determines the optimal metric projected CRS for a geometry.
        If source CRS is already projected, retains it.
        If source CRS is geographic (degrees), computes the local UTM zone
        based on the feature's centroid.
        """
        if source_crs.is_projected:
            epsg_code = source_crs.to_epsg()
            name = f"EPSG:{epsg_code}" if epsg_code else source_crs.name
            return source_crs, name

        # Geographic coordinates: find centroid (lon, lat)
        centroid = geometry.centroid
        lon, lat = centroid.x, centroid.y

        # Clamp lon/lat for safe UTM calculation
        lon = max(-180.0, min(180.0, lon))
        lat = max(-90.0, min(90.0, lat))

        # Handle Polar coordinates
        if lat > 84.0:
            target_epsg = 3413  # Polar Stereographic North
            name = f"EPSG:{target_epsg} (UPS North)"
        elif lat < -80.0:
            target_epsg = 3031  # Polar Stereographic South
            name = f"EPSG:{target_epsg} (UPS South)"
        else:
            # Universal Transverse Mercator (UTM) Zone calculation
            # UTM Zone = floor((lon + 180) / 6) + 1
            utm_zone = int((lon + 180.0) / 6.0) + 1
            if utm_zone > 60:
                utm_zone = 60
            elif utm_zone < 1:
                utm_zone = 1

            if lat >= 0:
                target_epsg = 32600 + utm_zone
                name = f"EPSG:{target_epsg} (UTM Zone {utm_zone}N)"
            else:
                target_epsg = 32700 + utm_zone
                name = f"EPSG:{target_epsg} (UTM Zone {utm_zone}S)"

        target_crs = CRS.from_epsg(target_epsg)
        return target_crs, name

    def project_geometry(
        self, geometry: BaseGeometry, source_crs: CRS
    ) -> Tuple[BaseGeometry, str]:
        """
        Projects a geometry from geographic coordinates to an optimal
        metric projected coordinate system.

        Returns:
            Tuple[BaseGeometry, str]: The projected geometry and target CRS identifier.
        """
        if geometry.is_empty:
            return geometry, "EPSG:4326"

        target_crs, target_name = self.determine_optimal_projected_crs(geometry, source_crs)

        # If already matching, return directly
        if source_crs == target_crs:
            return geometry, target_name

        try:
            transformer = Transformer.from_crs(
                source_crs, target_crs, always_xy=True
            )
            projected_geom = shapely.transform(
                geometry,
                lambda coords: np.column_stack(
                    transformer.transform(coords[:, 0], coords[:, 1])
                ),
            )
            return projected_geom, target_name
        except Exception as e:
            logger.error(f"Error projecting geometry to {target_name}: {e}")
            raise CRSTransformationException(f"Failed to project geometry: {e}")

    def compute_geodesic_polygon_area(self, geometry: BaseGeometry) -> float:
        """
        Calculates exact ellipsoidal geodesic area on WGS84 ellipsoid.
        Used as independent verification for geographic polygons.
        """
        try:
            area, _ = self._geod.geometry_area_perimeter(geometry)
            return abs(area)
        except Exception:
            return 0.0

    def compute_geodesic_linestring_length(self, geometry: BaseGeometry) -> float:
        """
        Calculates exact ellipsoidal geodesic length on WGS84 ellipsoid.
        """
        try:
            return abs(self._geod.geometry_length(geometry))
        except Exception:
            return 0.0

crs_service = CRSService()
