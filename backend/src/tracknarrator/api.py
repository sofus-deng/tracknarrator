"""FastAPI application for Track Narrator."""

import io
import json
import time
import zipfile
from typing import Dict, Any, Union

from fastapi import FastAPI, UploadFile, HTTPException, Query, File, Request, Body
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware

from .config import get_settings, SHARE_TTL_S_DEFAULT, TN_CORS_ORIGINS
from .share import sign_share_token, verify_share_token, jti_from_token
from .storage import list_shares as storage_list_shares, revoke_share as storage_revoke_share, add_share
from .importers.mylaps_sections_csv import MYLAPSSectionsCSVImporter
from .importers.trd_long_csv import TRDLongCSVImporter
from .importers.weather_csv import WeatherCSVImporter
from .importers.racechrono_csv import RaceChronoCSVImporter
from .importers.gpx import sniff_gpx, parse_gpx_to_bundle
from .store import store
from .storage import init_db, upsert_session, list_sessions, delete_session, get_session_bundle
from .schema import SessionBundle
from .events import detect_events, top5_events, build_sparklines
from .narrative import build_narrative
from .cards import build_share_cards
from .coach import coach_tips
from .viz import lap_deltas, section_box_stats
from .coach_score import compute_coach_score

# Constants for seed endpoint
MAX_BYTES = 2 * 1024 * 1024  # 2MB guard
MAX_RACECHRONO_BYTES = 10 * 1024 * 1024  # 10MB guard for RaceChrono


# Initialize database on module import
init_db()

# Create FastAPI app
app = FastAPI(
    title="Track Narrator API",
    description="API for importing and managing racing data",
    version="0.0.1"
)

# CORS: opt-in via env
origins = [o.strip() for o in (TN_CORS_ORIGINS or "").split(",") if o.strip()]
if origins or TN_CORS_ORIGINS.strip() == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if TN_CORS_ORIGINS.strip() == "*" else origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
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
    except (ValueError, AssertionError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bad_input",
                "source": "mylaps",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "unexpected_error",
                "message": str(e)
            }
        )


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
        text = content.decode("utf-8", errors="ignore")
        file_obj = io.BytesIO(content)
        
        # Import data
        result = TRDLongCSVImporter.import_file(file_obj, session_id)
        
        if result.bundle is None:
            # Get diagnostics from inspector
            try:
                inspection_info = TRDLongCSVImporter.inspect_text(text)
                missing_channels = inspection_info.get("missing_expected", [])
            except Exception:
                missing_channels = []
            
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "bad_trd_csv",
                    "message": "No valid telemetry rows found",
                    "details": {
                        "missing_channels": missing_channels,
                        "hint": "Ensure ts_ms,name,value headers; include speed, aps, gear, accx_can, accy_can, Steering_Angle, VBOX_Lat_Min, VBOX_Long_Minutes."
                    }
                }
            )
        
        # Merge into store
        counts, warnings = store.merge_bundle(session_id, result.bundle, "trd_long_csv")
        warnings.extend(result.warnings)
        
        return {
            "status": "success",
            "session_id": session_id,
            "counts": counts,
            "warnings": warnings
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions to be handled by the HTTP exception handler
        raise
    except (ValueError, AssertionError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bad_input",
                "source": "trd_long",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "unexpected_error",
                "message": str(e)
            }
        )


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
        
    except HTTPException as he:
        # Re-raise HTTP exceptions to be handled by the HTTP exception handler
        raise
    except (ValueError, AssertionError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bad_input",
                "source": "weather",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "unexpected_error",
                "message": str(e)
            }
        )


@app.post("/ingest/racechrono")
async def ingest_racechrono(
    session_id: str = Query(..., description="Session ID for the data"),
    file: UploadFile = File(..., description="RaceChrono CSV file")
) -> Dict[str, Any]:
    """
    Ingest RaceChrono CSV telemetry data.
    
    Args:
        session_id: Session ID for the data
        file: RaceChrono CSV file
        
    Returns:
        Dictionary with counts and warnings
    """
    try:
        # Read file content with size guard
        content = await file.read()
        if len(content) > MAX_RACECHRONO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (> {MAX_RACECHRONO_BYTES // (1024*1024)}MB)"
            )
        
        file_obj = io.BytesIO(content)
        
        # Import data
        result = RaceChronoCSVImporter.import_file(file_obj, session_id)
        
        if result.bundle is None:
            raise HTTPException(status_code=400, detail=f"Import failed: {result.warnings}")
        
        # Merge into store
        counts, warnings = store.merge_bundle(session_id, result.bundle, "racechrono_csv")
        warnings.extend(result.warnings)
        
        return {
            "status": "success",
            "session_id": session_id,
            "counts": counts,
            "warnings": warnings
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions to be handled by the HTTP exception handler
        raise
    except (ValueError, AssertionError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bad_input",
                "source": "racechrono",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "unexpected_error",
                "message": str(e)
            }
        )


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
        
        # Also persist to storage
        storage_session_id = upsert_session(bundle.model_dump(), name=f"seed_{sid}")
        
        return {
            "ok": True,
            "mode": "json",
            "session_id": sid,
            "storage_session_id": storage_session_id,
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
        
        # Also persist to storage
        storage_session_id = upsert_session(bundle.model_dump(), name=f"seed_{sid}")
        
        return {
            "ok": True,
            "mode": "file",
            "session_id": sid,
            "storage_session_id": storage_session_id,
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


@app.get("/session/{session_id}/viz")
async def get_viz(session_id: str) -> Dict[str, Any]:
    """
    Returns visualization-ready series derived from existing sparklines payload.
    Shape:
    {
      "lap_delta_series": [{"lap_no": int, "lap_ms": number, "delta_ms_to_median": number, "delta_ma3": number}, ...],
      "section_box": [{"section_no": int, "p10": num, "p25": num, "p50": num, "p75": num, "p90": num, "best_ms": num}, ...]
    }
    """
    # Reuse your existing summary builder to fetch sparklines
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Build sparklines
    sparklines = build_sparklines(bundle)
    
    # Extract data for visualization
    laps_ms = sparklines.get("laps_ms") or []
    sections = sparklines.get("sections_ms") or []
    
    # Convert laps_ms to expected format for lap_deltas
    laps_formatted = []
    for i, lap_ms in enumerate(laps_ms):
        laps_formatted.append({"lap_no": i+1, "lap_ms": lap_ms})
    
    # Convert sections_ms to expected format for section_box_stats
    # sections_ms is a dict with section names as keys, convert to 2D list
    sections_list = []
    if sections:
        # Find the maximum number of laps across all sections
        max_laps = max(len(values) for values in sections.values()) if sections else 0
        
        # Create 2D array [laps][sections]
        for lap_idx in range(max_laps):
            lap_sections = []
            for section_name in sorted(sections.keys()):
                if lap_idx < len(sections[section_name]):
                    lap_sections.append(sections[section_name][lap_idx])
                else:
                    lap_sections.append(None)
            sections_list.append(lap_sections)
    
    return {
        "lap_delta_series": lap_deltas(laps_formatted),
        "section_box": section_box_stats(sections_list),
    }


@app.get("/session/{session_id}/coach")
def get_coach_score(session_id: str, lang: str = Query(default="zh-Hant")):
    # reuse same summary/sparklines source to ensure determinism
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Build sparklines and get events for scoring
    sparklines = build_sparklines(bundle)
    events = top5_events(bundle)
    
    return compute_coach_score(sparklines, events, lang=lang)


@app.get("/session/{session_id}/narrative")
async def get_session_narrative(
    session_id: str,
    lang: str = Query("zh-Hant", description="Language for narrative (zh-Hant or en)"),
    ai_native: str = Query("auto", description="AI-native mode (on/off/auto)")
) -> Dict[str, Any]:
    """
    Get AI-native narrative for a session.
    
    Args:
        session_id: Session ID to retrieve narrative for
        lang: Language code for narrative
        ai_native: AI-native mode override
        
    Returns:
        Dictionary with narrative data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Get AI-native setting
    settings = get_settings()
    
    # Determine AI-native mode
    if ai_native == "auto":
        use_ai_native = settings.ai_native
    else:
        use_ai_native = ai_native.lower() in ("on", "true", "1", "yes", "enabled")
    
    # Get top 5 events for narrative
    top5 = top5_events(bundle)
    
    # Build narrative using new v0.2 function
    lines = build_narrative(bundle, top5, lang=lang, max_lines=3, ai_native=use_ai_native)
    
    return {
        "lines": lines,
        "lang": lang,
        "ai_native": use_ai_native
    }


@app.get("/session/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    ai_native: str = Query("auto", description="Include narrative in AI-native mode (on/off/auto)")
) -> Dict[str, Any]:
    """
    Get comprehensive session summary with events, cards, and sparklines.
    
    Args:
        session_id: Session ID to retrieve summary for
        ai_native: Whether to include narrative field
        
    Returns:
        Dictionary with events, cards, sparklines, and optionally narrative
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Get top 5 events
    events = top5_events(bundle)
    
    # Build share cards
    cards = build_share_cards(bundle)
    
    # Build sparklines
    sparklines = build_sparklines(bundle)
    
    # Base summary response
    response = {
        "events": events,
        "cards": cards,
        "sparklines": sparklines
    }
    
    # Add narrative field only if ai_native=on
    if ai_native.lower() in ("on", "true", "1", "yes", "enabled"):
        # Get AI-native setting
        settings = get_settings()
        use_ai_native = settings.ai_native
        
        # Build narrative
        lines = build_narrative(bundle, events, lang="zh-Hant", max_lines=3, ai_native=use_ai_native)
        
        response["narrative"] = {
            "lines": lines,
            "lang": "zh-Hant",
            "ai_native": use_ai_native
        }
    
    return response


@app.get("/session/{session_id}/export")
async def get_session_export(
    session_id: str,
    lang: str = Query("zh-Hant", description="Language for coaching tips and narrative")
) -> Response:
    """
    Get session export pack as ZIP file.
    
    Args:
        session_id: Session ID to export
        lang: Language for coaching tips and narrative ("zh-Hant" or "en")
        
    Returns:
        ZIP file containing all session data
    """
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Get top 5 events
    events = top5_events(bundle)
    
    # Build share cards
    cards = build_share_cards(bundle)
    
    # Build sparklines
    sparklines = build_sparklines(bundle)
    
    # Build coaching tips
    coach_tips_data = coach_tips(bundle, events, lang=lang)
    
    # Build narrative for export
    settings = get_settings()
    narrative_lines = build_narrative(bundle, events, lang=lang, max_lines=3, ai_native=settings.ai_native)
    narrative_data = {
        "lines": narrative_lines,
        "lang": lang,
        "ai_native": settings.ai_native
    }
    
    # Build KPIs
    total_laps = len(bundle.laps)
    best_lap_ms = min([lap.laptime_ms for lap in bundle.laps if lap.laptime_ms > 0], default=0)
    
    # Calculate median lap time
    valid_lap_times = [lap.laptime_ms for lap in bundle.laps if lap.laptime_ms > 0]
    if valid_lap_times:
        sorted_times = sorted(valid_lap_times)
        n = len(sorted_times)
        if n % 2 == 0:
            median_lap_ms = (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
        else:
            median_lap_ms = sorted_times[n//2]
    else:
        median_lap_ms = 0
    
    # Calculate session duration (if we have telemetry timestamps)
    session_duration_ms = 0
    if bundle.telemetry:
        timestamps = [t.ts_ms for t in bundle.telemetry if t.ts_ms is not None]
        if timestamps:
            session_duration_ms = max(timestamps) - min(timestamps)
    
    kpis = {
        "total_laps": total_laps,
        "best_lap_ms": best_lap_ms,
        "median_lap_ms": median_lap_ms,
        "session_duration_ms": session_duration_ms
    }
    
    # Create summary data
    summary_data = {
        "events": events,
        "cards": cards,
        "sparklines": sparklines
    }
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add summary.json
        zip_file.writestr("summary.json", json.dumps(summary_data, ensure_ascii=False, indent=2))
        
        # Add coach_tips.json
        zip_file.writestr("coach_tips.json", json.dumps(coach_tips_data, ensure_ascii=False, indent=2))
        
        # Add events.json
        zip_file.writestr("events.json", json.dumps(events, ensure_ascii=False, indent=2))
        
        # Add cards.json
        zip_file.writestr("cards.json", json.dumps(cards, ensure_ascii=False, indent=2))
        
        # Add sparklines.json
        zip_file.writestr("sparklines.json", json.dumps(sparklines, ensure_ascii=False, indent=2))
        
        # Add narrative.json
        zip_file.writestr("narrative.json", json.dumps(narrative_data, ensure_ascii=False, indent=2))
        
        # Add kpis.json
        zip_file.writestr("kpis.json", json.dumps(kpis, ensure_ascii=False, indent=2))
        
        # Add coach_score.json
        coach_score = compute_coach_score(sparklines, events, lang=lang)
        zip_file.writestr("coach_score.json", json.dumps(coach_score, ensure_ascii=False, separators=(",",":")))
    
    zip_buffer.seek(0)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={session_id}_export.zip"}
    )


@app.post("/dev/inspect/trd-long")
async def dev_inspect_trd_long(file: UploadFile = File(...)):
    """
    Inspect TRD long CSV file to diagnose channel mappings.
    
    Args:
        file: TRD long CSV file to inspect
        
    Returns:
        Dictionary with inspection results
    """
    try:
        # Read file content
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        
        # Inspect the file
        info = TRDLongCSVImporter.inspect_text(text)
        
        return {
            "status": "ok",
            "inspect": info
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions to be handled by the HTTP exception handler
        raise
    except (ValueError, AssertionError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bad_input",
                "source": "trd_inspect",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "unexpected_error",
                "message": str(e)
            }
        )


@app.post("/dev/inspect/weather")
async def dev_inspect_weather(file: UploadFile = File(...)):
    """
    Inspect weather CSV file to diagnose field mappings.
    
    Args:
        file: Weather CSV file to inspect
        
    Returns:
        Dictionary with inspection results including headers, recognized mapping, and reasons
    """
    try:
        # Read file content
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        # Inspect the file using new inspect_weather_csv function
        info = WeatherCSVImporter.inspect_weather_csv(file_obj)
        
        return {
            "status": "ok",
            "inspect": info
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions to be handled by the HTTP exception handler
        raise
    except (ValueError, AssertionError, ValidationError) as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bad_input",
                "source": "weather_inspect",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "unexpected_error",
                "message": str(e)
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent error format."""
    # Extract details from exc.detail if it's a dict, otherwise use as string
    if isinstance(exc.detail, dict):
        # If detail is a dict, extract message and details separately
        message = exc.detail.get("message", str(exc.detail))
        # If the dict already has a nested details structure, use it directly
        if "details" in exc.detail and isinstance(exc.detail["details"], dict):
            details = exc.detail["details"]
        else:
            # Otherwise, use the whole dict as details (excluding the message)
            details = {k: v for k, v in exc.detail.items() if k != "message"}
    else:
        message = str(exc.detail)
        details = None
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "type": "http_error",
                "message": message,
                "details": details
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with consistent error format."""
    import traceback
    # Log the traceback for debugging
    traceback.print_exc()
    
    # Re-raise HTTPExceptions to be handled by the HTTPException handler
    if isinstance(exc, HTTPException):
        raise exc
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "type": "internal_error",
                "message": "Internal server error",
                "details": str(exc)
            }
        }
    )
# === resilient error handlers (appended by Roo) ===
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

_logger = logging.getLogger("tracknarrator.api")

@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException):
    """
    Preserve HTTPException status codes and return a unified JSON shape.
    Also unwrap legacy messages that wrapped a 400 as 500, e.g.:
      'Error processing file: 400: Import failed: [...]'
    """
    status = exc.status_code
    detail = exc.detail
    message = None
    details = None

    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("detail") or str(detail)
        # keep the rest as details, but preserve the "code" field if it exists
        details = {k: v for k, v in detail.items() if k not in ("message", "detail")}
        # If the dict already has a nested details structure, use it directly
        if "details" in detail and isinstance(detail["details"], dict):
            # Merge the outer details with the inner details, preserving "code"
            inner_details = detail["details"]
            merged_details = {k: v for k, v in details.items() if k != "details"}
            merged_details.update(inner_details)
            details = merged_details
    else:
        message = str(detail)
        # Heuristic: if 500 was raised with a message that clearly indicates a 400,
        # downgrade to 400 so clients can act on it.
        if status == 500 and isinstance(detail, str):
            txt = detail
            if "400:" in txt or "No valid telemetry rows found" in txt:
                status = 400
                details = {"code": "bad_input", "raw": txt}

    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": status,
                "type": "http_error",
                "message": message,
                "details": details,
            }
        },
    )

@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    # Do NOT swallow HTTPException into 500 — re-raise to be handled above.
    if isinstance(exc, HTTPException):
        raise exc
    _logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "type": "internal_error",
                "message": str(exc),
                "details": None,
            }
        },
    )
# === end resilient error handlers ===


@app.post("/share/{session_id}")
async def create_share_token(
    session_id: str,
    ttl_s: int = Query(default=SHARE_TTL_S_DEFAULT, description="Time to live in seconds"),
    label: str | None = None
) -> Dict[str, Any]:
    """
    Create a shareable token for a session.
    
    Args:
        session_id: Session ID to create share token for
        ttl_s: Time to live in seconds (default from config)
        label: Optional label for the share
        
    Returns:
        Dictionary with token, expiration timestamp, share URL, and label
    """
    # Verify session exists
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Create token with expiration
    exp_ts = int(time.time()) + ttl_s
    token = sign_share_token(session_id, exp_ts)
    
    # sign_share_token already added a share record; if label present, update it:
    jti = jti_from_token(token)
    if jti:
        try:
            add_share(jti, session_id, exp_ts, label=label)
        except Exception:
            pass
    
    # Return token and metadata
    return {
        "token": token,
        "expire_at": exp_ts,
        "url": f"/shared/{token}/summary",
        "label": label
    }


@app.get("/shared/{token}/summary")
async def get_shared_summary(
    token: str,
    ai_native: str = Query("auto", description="Include narrative in AI-native mode (on/off/auto)"),
    lang: str = Query("zh-Hant", description="Language for narrative (zh-Hant or en)")
) -> Dict[str, Any]:
    """
    Get session summary via share token.
    
    Args:
        token: Share token
        ai_native: Whether to include narrative field
        lang: Language for narrative
        
    Returns:
        Session summary data
    """
    # Verify token
    is_valid, session_id, error = verify_share_token(token)
    if not is_valid:
        if error == "expired":
            raise HTTPException(status_code=410, detail="Share link has expired")
        elif error == "bad_signature":
            raise HTTPException(status_code=401, detail="Invalid share link")
        else:
            raise HTTPException(status_code=400, detail="Malformed share link")
    
    # Get session bundle
    bundle = store.get_bundle(session_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get top 5 events
    events = top5_events(bundle)
    
    # Build share cards
    cards = build_share_cards(bundle)
    
    # Build sparklines
    sparklines = build_sparklines(bundle)
    
    # Build KPIs
    total_laps = len(bundle.laps)
    best_lap_ms = min([lap.laptime_ms for lap in bundle.laps if lap.laptime_ms > 0], default=0)
    
    # Calculate median lap time
    valid_lap_times = [lap.laptime_ms for lap in bundle.laps if lap.laptime_ms > 0]
    if valid_lap_times:
        sorted_times = sorted(valid_lap_times)
        n = len(sorted_times)
        if n % 2 == 0:
            median_lap_ms = (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
        else:
            median_lap_ms = sorted_times[n//2]
    else:
        median_lap_ms = 0
    
    # Calculate session duration (if we have telemetry timestamps)
    session_duration_ms = 0
    if bundle.telemetry:
        timestamps = [t.ts_ms for t in bundle.telemetry if t.ts_ms is not None]
        if timestamps:
            session_duration_ms = max(timestamps) - min(timestamps)
    
    kpis = {
        "total_laps": total_laps,
        "best_lap_ms": best_lap_ms,
        "median_lap_ms": median_lap_ms,
        "session_duration_ms": session_duration_ms
    }
    
    # Base summary response
    response = {
        "events": events,
        "cards": cards,
        "sparklines": sparklines,
        "kpis": kpis
    }
    
    # Add narrative field only if ai_native=on
    if ai_native.lower() in ("on", "true", "1", "yes", "enabled"):
        # Get AI-native setting
        settings = get_settings()
        use_ai_native = settings.ai_native
        
        # Build narrative
        lines = build_narrative(bundle, events, lang=lang, max_lines=3, ai_native=use_ai_native)
        
        response["narrative"] = {
            "lines": lines,
            "lang": lang,
            "ai_native": use_ai_native
        }
    
    return response

@app.get("/shares")
async def list_shares(session_id: str | None = None):
    """List active shares (not revoked and not expired)."""
    return storage_list_shares(session_id=session_id)

@app.delete("/share/{token}", status_code=204)
async def revoke_share(token: str):
    """Revoke a share token."""
    jti = jti_from_token(token)
    if not jti:
        raise HTTPException(status_code=400, detail="malformed token")
    storage_revoke_share(jti)
    return Response(status_code=204)


@app.get("/sessions")
async def get_sessions(
    limit: int = Query(50, description="Maximum number of sessions to return"),
    offset: int = Query(0, description="Number of sessions to skip")
) -> Dict[str, Any]:
    """
    Get list of all sessions.
    
    Args:
        limit: Maximum number of sessions to return
        offset: Number of sessions to skip
        
    Returns:
        Dictionary with list of sessions
    """
    sessions = list_sessions(limit=limit, offset=offset)
    return {"sessions": sessions}


@app.delete("/session/{session_id}")
async def delete_session_endpoint(session_id: str) -> Response:
    """
    Delete a session by ID.
    
    Args:
        session_id: Session ID to delete
        
    Returns:
        204 on success, 404 if not found
    """
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Also remove from in-memory store if applicable
    if session_id in store.sessions:
        del store.sessions[session_id]
    
    return Response(status_code=204)


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(..., description="File to upload (CSV, GPX, or ZIP)"),
    name: str = Query(None, description="Optional name for the session"),
    tz: str = Query(None, description="Optional timezone for the session")
) -> Dict[str, Any]:
    """
    Upload a file for processing.
    
    Accepts:
    - .csv (RaceChrono or TRD long format)
    - .gpx (GPS track files)
    - .zip (containing supported files, picks first recognizable)
    
    Args:
        file: File to upload
        name: Optional name for the session
        tz: Optional timezone for the session
        
    Returns:
        Dictionary with session_id on success
    """
    try:
        # Read file content
        content = await file.read()
        filename = file.filename or ""
        
        # Check if it's a ZIP file
        if filename.lower().endswith('.zip'):
            # Process ZIP file
            with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                # Try to find a supported file in the ZIP
                for zip_info in zip_file.infolist():
                    zip_name = zip_info.filename.lower()
                    if zip_name.endswith('.csv'):
                        # Try to process as CSV
                        zip_content = zip_file.read(zip_info.filename)
                        if zip_content:
                            # Try RaceChrono first
                            try:
                                result = RaceChronoCSVImporter.import_file(
                                    io.BytesIO(zip_content),
                                    f"zip_{int(time.time()*1000)}"
                                )
                                if result.bundle:
                                    session_id = upsert_session(result.bundle.model_dump(), name=name)
                                    return {"session_id": session_id}
                            except:
                                pass
                            
                            # Try TRD long CSV
                            try:
                                result = TRDLongCSVImporter.import_file(
                                    io.BytesIO(zip_content),
                                    f"zip_{int(time.time()*1000)}"
                                )
                                if result.bundle:
                                    session_id = upsert_session(result.bundle.model_dump(), name=name)
                                    return {"session_id": session_id}
                            except:
                                pass
                    elif zip_name.endswith('.gpx'):
                        # Try GPX
                        zip_content = zip_file.read(zip_info.filename)
                        if zip_content:
                            try:
                                bundle = parse_gpx_to_bundle(
                                    zip_content,
                                    session_id=f"zip_{int(time.time()*1000)}",
                                    name=name
                                )
                                session_id = upsert_session(bundle.model_dump(), name=name)
                                return {"session_id": session_id}
                            except:
                                pass
                
                raise HTTPException(
                    status_code=400,
                    detail="No supported files found in ZIP"
                )
        
        # Check if it's a GPX file
        elif filename.lower().endswith('.gpx') or sniff_gpx(content):
            try:
                bundle = parse_gpx_to_bundle(
                    content,
                    session_id=f"gpx_{int(time.time()*1000)}",
                    name=name
                )
                session_id = upsert_session(bundle.model_dump(), name=name)
                return {"session_id": session_id}
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to process GPX file: {str(e)}"
                )
        
        # Check if it's a CSV file
        elif filename.lower().endswith('.csv'):
            # Try RaceChrono first
            try:
                result = RaceChronoCSVImporter.import_file(
                    io.BytesIO(content),
                    f"csv_{int(time.time()*1000)}"
                )
                if result.bundle:
                    session_id = upsert_session(result.bundle.model_dump(), name=name)
                    return {"session_id": session_id}
            except:
                pass
            
            # Try TRD long CSV
            try:
                result = TRDLongCSVImporter.import_file(
                    io.BytesIO(content),
                    f"csv_{int(time.time()*1000)}"
                )
                if result.bundle:
                    session_id = upsert_session(result.bundle.model_dump(), name=name)
                    return {"session_id": session_id}
            except:
                pass
            
            # Try MYLAPS sections CSV
            try:
                result = MYLAPSSectionsCSVImporter.import_file(
                    io.BytesIO(content),
                    f"csv_{int(time.time()*1000)}"
                )
                if result.bundle:
                    session_id = upsert_session(result.bundle.model_dump(), name=name)
                    return {"session_id": session_id}
            except:
                pass
            
            raise HTTPException(
                status_code=400,
                detail="Failed to process CSV file with any known format"
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type; expected RaceChrono/TRD CSV, GPX, or ZIP"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )