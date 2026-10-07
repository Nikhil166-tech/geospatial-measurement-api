from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_upload_kml_file(client: TestClient, sample_kml_path):
    with open(sample_kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample.kml"
    assert data["file_type"] == "kml"
    assert data["feature_count"] == 3
    assert data["status"] == "COMPLETED"
    assert data["crs"] == "EPSG:4326"

    file_id = data["id"]

    # 1. Test Get File Info
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["id"] == file_id
    assert info_data["feature_count"] == 3

    # 2. Test Get Measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["id"] == file_id
    assert len(meas_data["features"]) == 3
    assert meas_data["total_area_sq_meters"] is not None
    assert meas_data["total_length_meters"] is not None

    # Check Polygon feature
    poly_feat = next(f for f in meas_data["features"] if f["geometry_type"] == "Polygon")
    assert poly_feat["measurements"]["area_sq_meters"] > 0
    assert poly_feat["measurements"]["perimeter_meters"] > 0

    # Check LineString feature
    line_feat = next(f for f in meas_data["features"] if f["geometry_type"] == "LineString")
    assert line_feat["measurements"]["length_meters"] > 0
    assert line_feat["measurements"]["area_sq_meters"] is None

    # Check Point feature
    point_feat = next(f for f in meas_data["features"] if f["geometry_type"] == "Point")
    assert point_feat["measurements"]["area_sq_meters"] is None
    assert point_feat["measurements"]["length_meters"] is None

    # 3. Test GeoJSON features endpoint
    geo_resp = client.get(f"/api/files/{file_id}/features/")
    assert geo_resp.status_code == 200
    geo_data = geo_resp.json()
    assert geo_data["type"] == "FeatureCollection"
    assert len(geo_data["features"]) == 3

def test_upload_shapefile_zip(client: TestClient, sample_parcels_zip_path):
    with open(sample_parcels_zip_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("parcels.zip", f, "application/zip")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "parcels.zip"
    assert data["file_type"] == "shapefile"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"

    file_id = data["id"]
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert len(meas_data["features"]) == 2
    for feat in meas_data["features"]:
        assert feat["geometry_type"] == "Polygon"
        assert feat["measurements"]["area_sq_meters"] > 0

def test_upload_invalid_file_extension(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("data.txt", b"plain text data", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]

def test_get_nonexistent_file(client: TestClient):
    response = client.get("/api/files/nonexistent_id/")
    assert response.status_code == 404

def test_delete_file(client: TestClient, sample_flight_paths_zip_path):
    with open(sample_flight_paths_zip_path, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("flight_paths.zip", f, "application/zip")},
        )
    file_id = upload_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/files/{file_id}/")
    assert del_resp.status_code == 204

    # Verify 404 after deletion
    get_resp = client.get(f"/api/files/{file_id}/")
    assert get_resp.status_code == 404
