import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app"
routers_dir = os.path.join(base_dir, "routers")

# 1. routers/whatsapp.py
whatsapp_router_code = """from fastapi import APIRouter, HTTPException, Request
from app.services.whatsapp_service import process_farmer_interaction, get_farmer_session, update_session
from app.models.session import WhatsAppSimulateRequest

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

@router.post("/simulate-turn")
def simulate_interaction(payload: WhatsAppSimulateRequest):
    result = process_farmer_interaction(
        phone_number=payload.phone_number,
        message_body=payload.message_body or "",
        farmer_state=payload.farmer_state,
        language=payload.language,
        input_type=payload.input_type,
        voice_audio_note=payload.voice_audio_note,
        button_value=payload.button_value,
        root_cause_selected=payload.root_cause_selected
    )
    return result

@router.get("/session/{phone_number}")
def get_session(phone_number: str):
    sess = get_farmer_session(phone_number)
    if "_id" in sess:
        sess["_id"] = str(sess["_id"])
    return sess

@router.post("/session/{phone_number}/reset")
def reset_session(phone_number: str):
    update_session(phone_number, {
        "current_state": "IDLE",
        "active_gdb_id": None,
        "last_query": None,
        "nudge_scheduled": False
    })
    return {"status": "success", "message": f"Session for {phone_number} reset to IDLE"}

@router.post("/webhook")
async def webhook_handler(request: Request):
    try:
        body = await request.json()
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        messages = changes.get("value", {}).get("messages", [])
        if messages:
            msg = messages[0]
            from_phone = msg.get("from")
            text = msg.get("text", {}).get("body", "")
            res = process_farmer_interaction(phone_number=from_phone, message_body=text)
            return {"status": "success", "result": res}
        return {"status": "no_messages"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
"""
with open(os.path.join(routers_dir, "whatsapp.py"), "w", encoding="utf-8") as f:
    f.write(whatsapp_router_code)

# 2. routers/gdb.py
gdb_router_code = """from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
from app.database import get_db
import re

router = APIRouter(prefix="/gdb", tags=["GDB Catalog"])

@router.get("/entries")
def list_gdb_entries(
    crop: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    db = get_db()
    query: Dict[str, Any] = {}
    if crop and crop != "ALL":
        query["crop"] = {"$regex": crop, "$options": "i"}
    if domain and domain != "ALL":
        query["domain"] = domain
    if status and status != "ALL":
        query["status"] = status
    if search:
        s = re.escape(search)
        query["$or"] = [
            {"_id": {"$regex": s, "$options": "i"}},
            {"question_hi": {"$regex": s, "$options": "i"}},
            {"question_en": {"$regex": s, "$options": "i"}},
            {"sub_domain": {"$regex": s, "$options": "i"}},
            {"answer_hi": {"$regex": s, "$options": "i"}},
            {"answer_en": {"$regex": s, "$options": "i"}}
        ]
        
    total = db["gdb_entries"].count_documents(query)
    skip = (page - 1) * limit
    cursor = db["gdb_entries"].find(query).skip(skip).limit(limit).sort("metrics.helpful_ratio", 1)
    
    return {"total": total, "page": page, "limit": limit, "entries": list(cursor)}

@router.get("/entries/{gdb_id}")
def get_entry(gdb_id: str):
    db = get_db()
    e = db["gdb_entries"].find_one({"_id": gdb_id})
    if not e:
        raise HTTPException(status_code=404, detail="Not found")
    return e
"""
with open(os.path.join(routers_dir, "gdb.py"), "w", encoding="utf-8") as f:
    f.write(gdb_router_code)

# 3. routers/analytics.py
analytics_router_code = """from fastapi import APIRouter
from app.services.feedback_service import (
    get_analytics_overview,
    get_domain_analytics,
    get_state_analytics,
    get_root_cause_analytics
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
def overview():
    return get_analytics_overview()

@router.get("/domains")
def domains():
    return get_domain_analytics()

@router.get("/states")
def states():
    return get_state_analytics()

@router.get("/root-causes")
def root_causes():
    return get_root_cause_analytics()
"""
with open(os.path.join(routers_dir, "analytics.py"), "w", encoding="utf-8") as f:
    f.write(analytics_router_code)

# 4. routers/flagged.py
flagged_router_code = """from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.config import settings
from app.services.flagging_pipeline import resolve_flagged_entry

router = APIRouter(prefix="/flagged", tags=["Flagged Reviews"])

class ResolveRequest(BaseModel):
    revised_answer_hi: str
    revised_answer_en: str
    reviewer_note: str
    action: str = "REVISE_AND_REVALIDATE"

class ThresholdConfigRequest(BaseModel):
    helpful_threshold: float
    min_responses: int

@router.get("/queue")
def get_queue(status: Optional[str] = None):
    db = get_db()
    q = {}
    if status and status != "ALL":
        q["review_status"] = status
    items = list(db["flagged_queue"].find(q).sort("helpful_ratio", 1))
    return {"total": len(items), "queue": items}

@router.post("/{gdb_id}/resolve")
def resolve(gdb_id: str, payload: ResolveRequest):
    return resolve_flagged_entry(
        gdb_id=gdb_id,
        revised_answer_hi=payload.revised_answer_hi,
        revised_answer_en=payload.revised_answer_en,
        reviewer_note=payload.reviewer_note,
        action=payload.action
    )

@router.get("/config")
def get_config():
    return {"helpful_threshold": settings.FLAG_HELPFUL_THRESHOLD, "min_responses": settings.FLAG_MIN_RESPONSES}

@router.post("/config")
def update_config(payload: ThresholdConfigRequest):
    settings.FLAG_HELPFUL_THRESHOLD = payload.helpful_threshold
    settings.FLAG_MIN_RESPONSES = payload.min_responses
    return {"status": "success", "config": {"helpful_threshold": settings.FLAG_HELPFUL_THRESHOLD, "min_responses": settings.FLAG_MIN_RESPONSES}}
"""
with open(os.path.join(routers_dir, "flagged.py"), "w", encoding="utf-8") as f:
    f.write(flagged_router_code)

# 5. routers/digest.py
digest_router_code = """from fastapi import APIRouter
from app.services.digest_service import generate_weekly_agri_digest

router = APIRouter(prefix="/digest", tags=["Weekly Agri Digest"])

@router.get("/weekly")
def get_digest():
    return generate_weekly_agri_digest()
"""
with open(os.path.join(routers_dir, "digest.py"), "w", encoding="utf-8") as f:
    f.write(digest_router_code)

# 6. routers/weather.py
weather_router_code = """from fastapi import APIRouter, Query
from app.services.weather_service import get_imd_agro_alerts, get_crop_smart_advisory

router = APIRouter(prefix="/weather", tags=["IMD Weather"])

@router.get("/alerts")
def alerts():
    return get_imd_agro_alerts()

@router.get("/crop-advisory")
def advisory(crop: str = Query("Wheat")):
    return get_crop_smart_advisory(crop)
"""
with open(os.path.join(routers_dir, "weather.py"), "w", encoding="utf-8") as f:
    f.write(weather_router_code)

# 7. main.py
main_code = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.config import settings
from app.database import init_db, close_db
from app.routers import whatsapp, gdb, analytics, flagged, digest, weather

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ajrasakha")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Initializing {settings.PROJECT_NAME} v{settings.VERSION}...")
    init_db()
    yield
    close_db()
    logger.info("Shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Farmer Answer Feedback Loop & Automated Quality Pipeline for AjraSakha (ANNAM.AI / IIT Ropar)",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp.router, prefix=settings.API_V1_PREFIX)
app.include_router(gdb.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(flagged.router, prefix=settings.API_V1_PREFIX)
app.include_router(digest.router, prefix=settings.API_V1_PREFIX)
app.include_router(weather.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "ONLINE",
        "docs_url": "/docs",
        "supported_features": [
            "WhatsApp Two-Turn Feedback State Machine",
            "1-Tap Quick-Reply Buttons",
            "Multimodal Indic Voice Note Processing",
            "Smart Agro-Chrono Scheduling (Evening Leisure)",
            "Automated Statistical Flagging (<60%, N>=10)",
            "Weekly Agri Intelligence Digest",
            "IMD Agro-Meteorological Risk Matrix"
        ]
    }
"""
with open(os.path.join(base_dir, "main.py"), "w", encoding="utf-8") as f:
    f.write(main_code)

print("Generated all routers and main.py")
