"""FastAPI application for Track Narrator."""

import io
import json
from typing import Dict, Any, Union

from fastapi import FastAPI, UploadFile, HTTPException, Query, File, Request, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import get_settings
from .importers.mylaps_sections_csv import MYLAPSSectionsCSVImporter
from .importers.trd_long_csv import TRDLongCSVImporter
from .importers.weather_csv import WeatherCSVImporter
from .store import store
from .schema import SessionBundle
from .events import detect_events, top5_events, build_sparklines
from .narrative import build_narrative

# Constants for seed endpoint
MAX_BYTES = 2 * 1024 * 1024  # 2MB guard


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


@app.post("/dev/seed")
async def dev_seed(
    request: Request,
    file: Union[UploadFile, None] = File(default=None)
) -> Dict[str, Any]:
    """
    Seed the in-memory store with session data.
    
    Accepts either:
    1. JSON body with SessionBundle
    2. Multipart form with file field containing JSON
    
    Args:
        request: FastAPI request object
        file: Optional uploaded file with JSON data
        
    Returns:
        Dictionary with operation status, mode, session_id, counts and warnings
    """
    ctype = request.headers.get("content-type", "").lower()
    
    # Case A: JSON body
    if "application/json" in ctype:
        try:
            # Parse the JSON body manually
            body = await request.body()
            if not body:
                raise HTTPException(status_code=422, detail="Empty JSON body")
            
            payload = json.loads(body.decode("utf-8"))
            bundle = SessionBundle.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid seed JSON: {e}"
            ) from e
        
        sid = bundle.session.id
        counts, warnings = store.merge_bundle(sid, bundle, src="dev_seed_json")
        
        return {
            "ok": True,
            "mode": "json",
            "session_id": sid,
            "counts": counts,
            "warnings": warnings
        }
    
    # Case B: multipart with file
    if file is not None:
        data = await file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Seed file too large (> {MAX_BYTES} bytes)"
            )
        
        try:
            payload = json.loads(data.decode("utf-8"))
            bundle = SessionBundle.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid seed JSON: {e}"
            ) from e
        
        sid = bundle.session.id
        counts, warnings = store.merge_bundle(sid, bundle, src="dev_seed_file")
        
        return {
            "ok": True,
            "mode": "file",
            "session_id": sid,
            "counts": counts,
            "warnings": warnings
        }
    
    raise HTTPException(
        status_code=400,
        detail="Provide either JSON body or multipart file field 'file'"
    )


@app.get("/session/{session_id}/events")
async def get_session_events(session_id: str) -> Dict[str, Any]:
    """
    Get detected events for a session.
    
    Args:
        session_id: Session ID to retrieve events for
        
    Returns:
        Dictionary with all events and top 5 events
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Detect all events and get top 5
    all_events = detect_events(bundle)
    top5 = top5_events(bundle)
    
    return {
        "events": all_events,
        "top5": top5
    }


@app.get("/session/{session_id}/sparklines")
async def get_session_sparklines(session_id: str) -> Dict[str, Any]:
    """
    Get sparkline data for a session.
    
    Args:
        session_id: Session ID to retrieve sparklines for
        
    Returns:
        Dictionary with sparkline data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Build sparklines
    sparklines = build_sparklines(bundle)
    
    return sparklines


@app.get("/session/{session_id}/narrative")
async def get_session_narrative(session_id: str) -> Dict[str, Any]:
    """
    Get AI-native narrative for a session.
    
    Args:
        session_id: Session ID to retrieve narrative for
        
    Returns:
        Dictionary with narrative data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Get AI-native setting
    settings = get_settings()
    ai_native = settings.ai_native
    
    # Get top 5 events for narrative
    top5 = top5_events(bundle)
    
    # Build narrative
    narrative = build_narrative(bundle, top5, ai_native)
    
    return narrative


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