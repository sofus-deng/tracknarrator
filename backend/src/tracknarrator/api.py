"""FastAPI application for Track Narrator."""

import io
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, HTTPException, Query, File
from fastapi.responses import JSONResponse

from .config import get_settings
from .importers.mylaps_sections_csv import MYLAPSSectionsCSVImporter
from .importers.trd_long_csv import TRDLongCSVImporter
from .importers.weather_csv import WeatherCSVImporter
from .store import store
from .schema import SessionBundle


# Create FastAPI app
app = FastAPI(
    title="Track Narrator API",
    description="API for importing and managing racing data",
    version="0.0.1"
)


@app.get("/health")
async def health_check() -> Dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}


@app.get("/config")
async def get_config() -> Dict[str, Any]:
    """Get application configuration."""
    settings = get_settings()
    return {"ai_native": settings.ai_native}


@app.post("/ingest/mylaps-sections")
async def ingest_mylaps_sections(
    session_id: str = Query(..., description="Session ID for the data"),
    file: UploadFile = File(..., description="MYLAPS sections CSV file")
) -> Dict[str, Any]:
    """
    Ingest MYLAPS sections CSV data.
    
    Args:
        session_id: Session ID for the data
        file: MYLAPS sections CSV file
        
    Returns:
        Dictionary with counts and warnings
    """
    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        # Import data
        result = MYLAPSSectionsCSVImporter.import_file(file_obj, session_id)
        
        if result.bundle is None:
            raise HTTPException(status_code=400, detail=f"Import failed: {result.warnings}")
        
        # Merge into store
        counts, warnings = store.merge_bundle(session_id, result.bundle, "mylaps_sections_csv")
        warnings.extend(result.warnings)
        
        return {
            "status": "success",
            "session_id": session_id,
            "counts": counts,
            "warnings": warnings
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions to be handled by the HTTP exception handler
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/ingest/trd-long")
async def ingest_trd_long(
    session_id: str = Query(..., description="Session ID for the data"),
    file: UploadFile = File(..., description="TRD long CSV telemetry file")
) -> Dict[str, Any]:
    """
    Ingest TRD long CSV telemetry data.
    
    Args:
        session_id: Session ID for the data
        file: TRD long CSV telemetry file
        
    Returns:
        Dictionary with counts and warnings
    """
    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        # Import data
        result = TRDLongCSVImporter.import_file(file_obj, session_id)
        
        if result.bundle is None:
            raise HTTPException(status_code=400, detail=f"Import failed: {result.warnings}")
        
        # Merge into store
        counts, warnings = store.merge_bundle(session_id, result.bundle, "trd_long_csv")
        warnings.extend(result.warnings)
        
        return {
            "status": "success",
            "session_id": session_id,
            "counts": counts,
            "warnings": warnings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/ingest/weather")
async def ingest_weather(
    session_id: str = Query(..., description="Session ID for the data"),
    file: UploadFile = File(..., description="Weather CSV file")
) -> Dict[str, Any]:
    """
    Ingest weather CSV data.
    
    Args:
        session_id: Session ID for the data
        file: Weather CSV file
        
    Returns:
        Dictionary with counts and warnings
    """
    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        # Import data
        result = WeatherCSVImporter.import_file(file_obj, session_id)
        
        if result.bundle is None:
            raise HTTPException(status_code=400, detail=f"Import failed: {result.warnings}")
        
        # Merge into store
        counts, warnings = store.merge_bundle(session_id, result.bundle, "weather_csv")
        warnings.extend(result.warnings)
        
        return {
            "status": "success",
            "session_id": session_id,
            "counts": counts,
            "warnings": warnings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/session/{session_id}/bundle")
async def get_session_bundle(session_id: str) -> SessionBundle:
    """
    Get complete session bundle by ID.
    
    Args:
        session_id: Session ID to retrieve
        
    Returns:
        Complete session bundle with all data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return bundle


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with consistent error format."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "internal_error",
                "details": str(exc)
            }
        }
    )