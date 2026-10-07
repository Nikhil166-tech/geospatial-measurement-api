from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Tuple
from shapely.geometry.base import BaseGeometry

class ParsedFeature:
    """Internal representation of a parsed geospatial feature."""
    def __init__(
        self,
        feature_id: Any,
        geometry_type: str,
        geometry: BaseGeometry,
        properties: Dict[str, Any],
        crs: str
    ):
        self.feature_id = feature_id
        self.geometry_type = geometry_type
        self.geometry = geometry
        self.properties = properties
        self.crs = crs

class BaseGeospatialParser(ABC):
    """Abstract base class for all geospatial file format parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> Tuple[str, List[ParsedFeature]]:
        """
        Parses a geospatial file and returns:
        - crs: The Coordinate Reference System string (e.g. EPSG:4326)
        - features: List of ParsedFeature objects
        """
        pass
