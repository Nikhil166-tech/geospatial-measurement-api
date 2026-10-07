from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.endpoints import router as v1_files_router
from app.core.config import settings
from app.core.exceptions import GeospatialAPIException

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# Geospatial File Measurement API 🌍📐

A production-grade REST API service built with **FastAPI** for parsing, reprojecting, and measuring features within geospatial files (**KML** and **ESRI Shapefiles in ZIP format**).

### Features
* **Multi-Format Support:** Ingests `.kml` and zipped ESRI Shapefiles (`.shp`, `.shx`, `.dbf`, `.prj`).
* **Automated CRS Projection:** Automatically transforms geographic coordinates (e.g., `EPSG:4326`) into localized projected coordinate systems (**Universal Transverse Mercator - UTM**) to compute true metric measurements (square meters and meters).
* **Precise Geometric Measurements:**
  * **Polygons / MultiPolygons:** Area ($m^2$, $ha$, $km^2$) & Perimeter ($m$).
  * **LineStrings / MultiLineStrings:** Length ($m$, $km$).
  * **Points / MultiPoints:** Handled gracefully without errors.
  * **Unsupported Geometries:** Flagged gracefully without system crashes.
* **GeoJSON Feature Collection Export:** Retrieve extracted geometries formatted according to RFC 7946 GeoJSON.
    """,
    openapi_tags=[
        {
            "name": "Geospatial Files",
            "description": "Operations for uploading, retrieving, measuring, and deleting geospatial files.",
        },
        {"name": "System", "description": "System health and status probes."},
    ],
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global custom exception handler
@app.exception_handler(GeospatialAPIException)
async def geospatial_api_exception_handler(request: Request, exc: GeospatialAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "type": exc.__class__.__name__},
    )

# Include API routes under /api
app.include_router(v1_files_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["System"], summary="Health check probe")
@app.get("/api/health", tags=["System"], summary="API health check probe")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

@app.get("/", tags=["System"], include_in_schema=False)
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "api_v1": f"{settings.API_V1_PREFIX}/files",
    }
