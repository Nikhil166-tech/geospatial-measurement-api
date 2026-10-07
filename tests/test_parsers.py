from pathlib import Path
import pytest
import zipfile
from app.core.exceptions import InvalidFileFormatException
from app.services.parsers.kml_parser import kml_parser
from app.services.parsers.shapefile_parser import shapefile_parser

def test_parse_valid_kml(sample_kml_path):
    crs, features = kml_parser.parse(sample_kml_path)
    assert crs == "EPSG:4326"
    assert len(features) == 3

    geom_types = [f.geometry_type for f in features]
    assert "Polygon" in geom_types
    assert "LineString" in geom_types
    assert "Point" in geom_types

    # Verify properties extracted
    poly_feat = next(f for f in features if f.geometry_type == "Polygon")
    assert poly_feat.properties.get("name") == "Agricultural Survey Plot 1"
    assert poly_feat.properties.get("crop_type") == "Wheat"

    line_feat = next(f for f in features if f.geometry_type == "LineString")
    assert line_feat.properties.get("flight_speed_mps") == "12.5"

    point_feat = next(f for f in features if f.geometry_type == "Point")
    assert point_feat.properties.get("elevation_m") == "920.4"

def test_parse_valid_shapefile_polygons(sample_parcels_zip_path):
    crs, features = shapefile_parser.parse(sample_parcels_zip_path)
    assert "4326" in crs
    assert len(features) == 2
    for f in features:
        assert f.geometry_type == "Polygon"
        assert "name" in f.properties
        assert "crop" in f.properties

def test_parse_valid_shapefile_lines(sample_flight_paths_zip_path):
    crs, features = shapefile_parser.parse(sample_flight_paths_zip_path)
    assert "4326" in crs
    assert len(features) == 2
    for f in features:
        assert f.geometry_type == "LineString"
        assert "flight_id" in f.properties

def test_shapefile_missing_shp_raises_exception(tmp_path):
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as z:
        dummy_file = tmp_path / "dummy.txt"
        dummy_file.write_text("not a shp")
        z.write(dummy_file, arcname="dummy.txt")

    with pytest.raises(InvalidFileFormatException):
        shapefile_parser.parse(bad_zip)
