from typing import Any, Dict
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from app.core.exceptions import (
    FileProcessingException,
    InvalidFileFormatException,
    ResourceNotFoundException,
)
from app.models.schemas import (
    FileInfoResponse,
    FileListResponse,
    FileMeasurementsResponse,
)
from app.services.file_service import file_service

router = APIRouter(prefix="/files", tags=["Geospatial Files"])

@router.post(
    "/",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process geospatial file",
    description="Accepts a `.kml` file or a `.zip` archive containing an ESRI Shapefile (.shp, .shx, .dbf, .prj). Extracts features and calculates metric measurements.",
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.kml or .zip shapefile)")
):
    try:
        result = await file_service.process_uploaded_file(file)
        return result
    except InvalidFileFormatException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileProcessingException as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )

@router.get(
    "/",
    response_model=FileListResponse,
    summary="List uploaded files",
    description="Returns a paginated list of all uploaded files and their current processing status.",
)
def list_files(
    limit: int = Query(50, ge=1, le=100, description="Number of files to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    return file_service.list_files(limit=limit, offset=offset)

@router.get(
    "/{file_id}/",
    response_model=FileInfoResponse,
    summary="Get file information",
    description="Returns metadata about an uploaded file including feature count, CRS, and status.",
)
def get_file_info(file_id: str):
    try:
        return file_service.get_file_info(file_id)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/{file_id}/measurements/",
    response_model=FileMeasurementsResponse,
    summary="Get file measurements",
    description="Returns calculated metric measurements (area for Polygons, length for LineStrings) along with reprojection details for every feature.",
)
def get_file_measurements(file_id: str):
    try:
        return file_service.get_file_measurements(file_id)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/{file_id}/features/",
    summary="Get extracted features as GeoJSON",
    description="Returns the features extracted from the file in standard GeoJSON FeatureCollection format.",
)
def get_file_features_geojson(file_id: str):
    try:
        return file_service.get_file_features_geojson(file_id)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete(
    "/{file_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete uploaded file",
    description="Deletes the file metadata, calculated measurements, and local stored file.",
)
def delete_file(file_id: str):
    try:
        file_service.delete_file(file_id)
        return None
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
