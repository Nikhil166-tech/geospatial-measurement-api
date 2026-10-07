import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree.ElementTree import Element
import defusedxml.ElementTree as ET
from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    GeometryCollection,
)
from shapely.geometry.base import BaseGeometry
from app.core.exceptions import FileProcessingException
from app.services.parsers.base import BaseGeospatialParser, ParsedFeature

logger = logging.getLogger(__name__)

class KMLParser(BaseGeospatialParser):
    """
    Parser for OGC KML (Keyhole Markup Language) files.
    Robustly handles namespaces, extended metadata, Point, LineString,
    Polygon (with holes), and MultiGeometry types.
    """

    def parse(self, file_path: Path) -> Tuple[str, List[ParsedFeature]]:
        if not file_path.exists():
            raise FileProcessingException(f"KML file not found at {file_path}")

        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()
        except Exception as e:
            raise FileProcessingException(f"Malformed or invalid KML XML content: {e}")

        crs = "EPSG:4326"  # KML specification standard is always WGS84
        features: List[ParsedFeature] = []

        # Find all Placemark elements across any namespace
        placemarks = self._find_all_by_local_name(root, "Placemark")
        feature_index = 0

        for placemark in placemarks:
            props = self._extract_properties(placemark)
            geom = self._extract_geometry(placemark)
            geom_type = geom.geom_type if geom else "Unknown"

            features.append(
                ParsedFeature(
                    feature_id=props.get("id") or feature_index,
                    geometry_type=geom_type,
                    geometry=geom,
                    properties=props,
                    crs=crs,
                )
            )
            feature_index += 1

        return crs, features

    def _find_all_by_local_name(self, root: Element, tag_name: str) -> List[Element]:
        matches = []
        for elem in root.iter():
            local_tag = elem.tag.split("}")[-1]
            if local_tag == tag_name:
                matches.append(elem)
        return matches

    def _extract_properties(self, placemark: Element) -> Dict[str, Any]:
        props: Dict[str, Any] = {}
        if placemark.attrib.get("id"):
            props["id"] = placemark.attrib["id"]

        for child in placemark:
            tag = child.tag.split("}")[-1]
            if tag in ("name", "description", "styleUrl") and child.text:
                props[tag] = child.text.strip()
            elif tag == "ExtendedData":
                for data_node in child.iter():
                    dtag = data_node.tag.split("}")[-1]
                    if dtag == "Data":
                        attr_name = data_node.attrib.get("name")
                        val_node = self._find_first_child(data_node, "value")
                        if attr_name and val_node is not None and val_node.text:
                            props[attr_name] = val_node.text.strip()
                    elif dtag == "SimpleData":
                        attr_name = data_node.attrib.get("name")
                        if attr_name and data_node.text:
                            props[attr_name] = data_node.text.strip()

        return props

    def _find_first_child(self, parent: Element, local_name: str) -> Optional[Element]:
        for child in parent:
            if child.tag.split("}")[-1] == local_name:
                return child
        return None

    def _extract_geometry(self, placemark: Element) -> Optional[BaseGeometry]:
        for child in placemark:
            tag = child.tag.split("}")[-1]
            if tag == "Point":
                return self._parse_point(child)
            elif tag == "LineString":
                return self._parse_linestring(child)
            elif tag == "Polygon":
                return self._parse_polygon(child)
            elif tag == "MultiGeometry":
                return self._parse_multigeometry(child)
        return None

    def _parse_coordinates_string(self, text: Optional[str]) -> List[Tuple[float, float]]:
        if not text:
            return []
        coords: List[Tuple[float, float]] = []
        for token in text.strip().split():
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords

    def _parse_point(self, elem: Element) -> Optional[Point]:
        coords_node = self._find_first_child(elem, "coordinates")
        if coords_node is not None and coords_node.text:
            coords = self._parse_coordinates_string(coords_node.text)
            if coords:
                return Point(coords[0])
        return None

    def _parse_linestring(self, elem: Element) -> Optional[LineString]:
        coords_node = self._find_first_child(elem, "coordinates")
        if coords_node is not None and coords_node.text:
            coords = self._parse_coordinates_string(coords_node.text)
            if len(coords) >= 2:
                return LineString(coords)
        return None

    def _parse_polygon(self, elem: Element) -> Optional[Polygon]:
        outer_coords: List[Tuple[float, float]] = []
        inner_rings: List[List[Tuple[float, float]]] = []

        for child in elem:
            tag = child.tag.split("}")[-1]
            if tag == "outerBoundaryIs":
                linear_ring = self._find_first_child(child, "LinearRing")
                if linear_ring is not None:
                    coords_node = self._find_first_child(linear_ring, "coordinates")
                    if coords_node is not None and coords_node.text:
                        outer_coords = self._parse_coordinates_string(coords_node.text)
            elif tag == "innerBoundaryIs":
                linear_ring = self._find_first_child(child, "LinearRing")
                if linear_ring is not None:
                    coords_node = self._find_first_child(linear_ring, "coordinates")
                    if coords_node is not None and coords_node.text:
                        ring_coords = self._parse_coordinates_string(coords_node.text)
                        if len(ring_coords) >= 3:
                            inner_rings.append(ring_coords)

        if len(outer_coords) >= 3:
            return Polygon(shell=outer_coords, holes=inner_rings if inner_rings else None)
        return None

    def _parse_multigeometry(self, elem: Element) -> Optional[BaseGeometry]:
        geoms: List[BaseGeometry] = []
        for child in elem:
            tag = child.tag.split("}")[-1]
            if tag == "Point":
                g = self._parse_point(child)
            elif tag == "LineString":
                g = self._parse_linestring(child)
            elif tag == "Polygon":
                g = self._parse_polygon(child)
            elif tag == "MultiGeometry":
                g = self._parse_multigeometry(child)
            else:
                g = None

            if g is not None:
                geoms.append(g)

        if not geoms:
            return None
        return GeometryCollection(geoms)

kml_parser = KMLParser()
