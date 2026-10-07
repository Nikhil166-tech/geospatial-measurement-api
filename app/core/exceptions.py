class GeospatialAPIException(Exception):
    """Base exception for Geospatial Measurement API"""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class InvalidFileFormatException(GeospatialAPIException):
    def __init__(self, message: str = "Invalid or unsupported file format."):
        super().__init__(message, status_code=400)

class FileProcessingException(GeospatialAPIException):
    def __init__(self, message: str = "Failed to process geospatial file."):
        super().__init__(message, status_code=422)

class ResourceNotFoundException(GeospatialAPIException):
    def __init__(self, message: str = "Requested resource not found."):
        super().__init__(message, status_code=404)

class CRSTransformationException(GeospatialAPIException):
    def __init__(self, message: str = "Failed to transform coordinate reference system."):
        super().__init__(message, status_code=422)
