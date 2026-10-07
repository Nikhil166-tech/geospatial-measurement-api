import pytest
from shapely.geometry import Point, Polygon, LineString, MultiPoint
from app.services.measurement_service import measurement_service

def test_polygon_area_calculation():
    # Polygon in Bangalore (approx 550m x 550m = ~300,000 m²)
    poly = Polygon([(77.580, 12.970), (77.585, 12.970), (77.585, 12.975), (77.580, 12.975), (77.580, 12.970)])
    result = measurement_service.process_feature(
        feature_id=1,
        geometry=poly,
        source_crs_str="EPSG:4326",
        properties={"label": "Field 1"}
    )

    assert result.is_supported is True
    assert result.geometry_type == "Polygon"
    assert result.measurements is not None
    assert result.measurements.area_sq_meters is not None
    assert result.measurements.area_sq_meters > 250000
    assert result.measurements.area_hectares is not None
    assert result.measurements.perimeter_meters is not None
    assert "UTM Zone 43N" in result.projected_crs

def test_linestring_length_calculation():
    # LineString in Bangalore
    line = LineString([(77.580, 12.970), (77.585, 12.975)])
    result = measurement_service.process_feature(
        feature_id=2,
        geometry=line,
        source_crs_str="EPSG:4326",
        properties={"line_id": "L1"}
    )

    assert result.is_supported is True
    assert result.geometry_type == "LineString"
    assert result.measurements is not None
    assert result.measurements.length_meters is not None
    assert result.measurements.length_meters > 500
    assert result.measurements.length_km is not None
    assert result.measurements.area_sq_meters is None

def test_point_graceful_handling():
    # Point has no area or length
    pt = Point(77.580, 12.970)
    result = measurement_service.process_feature(
        feature_id=3,
        geometry=pt,
        source_crs_str="EPSG:4326",
        properties={"name": "Sensor 01"}
    )

    assert result.is_supported is True
    assert result.geometry_type == "Point"
    assert result.measurements.area_sq_meters is None
    assert result.measurements.length_meters is None
    assert "Point geometry does not have length or area" in result.measurements.notes

def test_null_or_empty_geometry_handling():
    empty_poly = Polygon()
    result = measurement_service.process_feature(
        feature_id=4,
        geometry=empty_poly,
        source_crs_str="EPSG:4326",
        properties={}
    )

    assert result.is_supported is False
    assert "null or empty" in result.measurements.notes
