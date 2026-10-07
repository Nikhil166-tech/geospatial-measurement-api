import pytest
from pyproj import CRS
from shapely.geometry import Point, Polygon, LineString
from app.services.crs_service import crs_service

def test_parse_crs():
    # Standard EPSG
    crs_obj, name = crs_service.parse_crs("EPSG:4326")
    assert crs_obj.to_epsg() == 4326
    assert name == "EPSG:4326"

    # None or empty defaults to EPSG:4326
    crs_obj2, name2 = crs_service.parse_crs(None)
    assert crs_obj2.to_epsg() == 4326
    assert name2 == "EPSG:4326"

    crs_obj3, name3 = crs_service.parse_crs("")
    assert crs_obj3.to_epsg() == 4326

    # Invalid string defaults safely to EPSG:4326
    crs_obj4, name4 = crs_service.parse_crs("INVALID_CRS_XYZ")
    assert crs_obj4.to_epsg() == 4326

def test_determine_optimal_projected_crs_utm_zones():
    source_crs = CRS.from_epsg(4326)

    # Bangalore, India (approx lon 77.59, lat 12.97) -> UTM Zone 43N (EPSG:32643)
    geom_india = Point(77.59, 12.97)
    target_crs, name = crs_service.determine_optimal_projected_crs(geom_india, source_crs)
    assert target_crs.to_epsg() == 32643
    assert "UTM Zone 43N" in name

    # San Francisco, USA (approx lon -122.41, lat 37.77) -> UTM Zone 10N (EPSG:32610)
    geom_sf = Point(-122.41, 37.77)
    target_crs_sf, name_sf = crs_service.determine_optimal_projected_crs(geom_sf, source_crs)
    assert target_crs_sf.to_epsg() == 32610
    assert "UTM Zone 10N" in name_sf

    # Sydney, Australia (approx lon 151.20, lat -33.86) -> UTM Zone 56S (EPSG:32756)
    geom_syd = Point(151.20, -33.86)
    target_crs_syd, name_syd = crs_service.determine_optimal_projected_crs(geom_syd, source_crs)
    assert target_crs_syd.to_epsg() == 32756
    assert "UTM Zone 56S" in name_syd

def test_already_projected_crs_preserved():
    projected_crs = CRS.from_epsg(32643)
    geom = Polygon([(100, 100), (200, 100), (200, 200), (100, 200), (100, 100)])
    target_crs, name = crs_service.determine_optimal_projected_crs(geom, projected_crs)
    assert target_crs.to_epsg() == 32643

def test_project_geometry_transformation():
    source_crs = CRS.from_epsg(4326)
    poly = Polygon([(77.58, 12.97), (77.59, 12.97), (77.59, 12.98), (77.58, 12.98), (77.58, 12.97)])
    projected_poly, target_crs_name = crs_service.project_geometry(poly, source_crs)

    assert projected_poly.geom_type == "Polygon"
    assert "32643" in target_crs_name
    # Coordinates in UTM meters should be in orders of magnitude of 100,000+
    minx, miny, maxx, maxy = projected_poly.bounds
    assert minx > 100000
    assert miny > 1000000
    assert projected_poly.area > 0
