import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app\services"

# 1. flagging_pipeline.py
flagging_pipeline_code = """from datetime import datetime
from typing import Dict, Any, Optional
import logging
from app.config import settings
from app.database import get_db

logger = logging.getLogger("ajrasakha.flagging")

def evaluate_and_flag_gdb(gdb_id: str) -> Optional[Dict[str, Any]]:
    \"\"\"
    Evaluates whether a GDB entry has dropped below the helpfulness threshold:
    Threshold: helpful_ratio < FLAG_HELPFUL_THRESHOLD (0.60)
    Condition: total_feedback >= FLAG_MIN_RESPONSES (10)
    \"\"\"
    db = get_db()
    gdb = db["gdb_entries"].find_one({"_id": gdb_id})
    if not gdb:
        return None
    
    metrics = gdb.get("metrics", {})
    upvotes = metrics.get("upvotes", 0)
    downvotes = metrics.get("downvotes", 0)
    total_fb = upvotes + downvotes
    
    if total_fb == 0:
        return None
        
    helpful_ratio = round(upvotes / total_fb, 3)
    
    # Update metrics on GDB entry
    db["gdb_entries"].update_one(
        {"_id": gdb_id},
        {"$set": {
            "metrics.total_feedback": total_fb,
            "metrics.upvotes": upvotes,
            "metrics.downvotes": downvotes,
            "metrics.helpful_ratio": helpful_ratio,
            "metrics.last_feedback_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    # Automated Flagging Logic
    is_failing = (total_fb >= settings.FLAG_MIN_RESPONSES) and (helpful_ratio < settings.FLAG_HELPFUL_THRESHOLD)
    
    if is_failing:
        # Collect recent negative feedback insights
        neg_feedbacks = list(db["farmer_feedback"].find(
            {"gdb_id": gdb_id, "rating": 2},
            {"farmer_state": 1, "language": 1, "feedback_reason": 1}
        ).sort("timestamp", -1).limit(20))
        
        states = [f.get("farmer_state", "Unknown") for f in neg_feedbacks if f.get("farmer_state")]
        most_affected_state = max(set(states), key=states.count) if states else "Multiple"
        
        flag_data = {
            "gdb_id": gdb_id,
            "crop": gdb.get("crop"),
            "domain": gdb.get("domain"),
            "question_en": gdb.get("question_en"),
            "question_hi": gdb.get("question_hi"),
            "current_answer_en": gdb.get("answer_en"),
            "current_answer_hi": gdb.get("answer_hi"),
            "helpful_ratio": helpful_ratio,
            "total_feedback": total_fb,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "threshold_configured": settings.FLAG_HELPFUL_THRESHOLD,
            "min_samples_configured": settings.FLAG_MIN_RESPONSES,
            "flagged_at": datetime.utcnow().isoformat(),
            "primary_negative_state": most_affected_state,
            "flag_reason": f"Helpfulness score ({int(helpful_ratio*100)}%) is below {int(settings.FLAG_HELPFUL_THRESHOLD*100)}% threshold across {total_fb} farmer responses.",
            "diagnostics": {
                "technical_level": gdb.get("technical_level", "Medium"),
                "detected_issues": [
                    "Language too technical or chemical brand names unfamiliar",
                    "Missing local dosage specifications for agro-climatic zone",
                    "Farmer reported treatment ineffective or too expensive"
                ]
            },
            "review_status": "PENDING_AGRI_REVIEW", # PENDING_AGRI_REVIEW, REVISED, RE_VALIDATED
            "assigned_team": "ACE Agronomy Board"
        }
        
        db["flagged_queue"].update_one(
            {"gdb_id": gdb_id},
            {"$set": flag_data},
            upsert=True
        )
        
        db["gdb_entries"].update_one(
            {"_id": gdb_id},
            {"$set": {"status": "FLAGGED_REVIEW"}}
        )
        logger.warning(f"GDB Entry {gdb_id} AUTOMATICALLY FLAGGED! Ratio: {helpful_ratio*100}% ({total_fb} responses)")
        return flag_data
    else:
        # If it had previously been flagged and has improved or was re-validated
        return None

def resolve_flagged_entry(gdb_id: str, revised_answer_hi: str, revised_answer_en: str, reviewer_note: str, action: str):
    db = get_db()
    
    if action == "REVISE_AND_REVALIDATE":
        # Update GDB entry with revised answer
        db["gdb_entries"].update_one(
            {"_id": gdb_id},
            {"$set": {
                "answer_hi": revised_answer_hi,
                "answer_en": revised_answer_en,
                "status": "RE_VALIDATED",
                "technical_level": "Simple", # simplified for farmers
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        
        db["flagged_queue"].update_one(
            {"gdb_id": gdb_id},
            {"$set": {
                "review_status": "RE_VALIDATED",
                "reviewer_note": reviewer_note,
                "resolved_at": datetime.utcnow().isoformat()
            }}
        )
        return {"status": "success", "message": f"Entry {gdb_id} revised and re-validated in GDB."}
    elif action == "SEND_TO_ACE_PIPELINE":
        db["flagged_queue"].update_one(
            {"gdb_id": gdb_id},
            {"$set": {
                "review_status": "SENT_TO_ACE_PIPELINE",
                "reviewer_note": reviewer_note,
                "sent_to_pipeline_at": datetime.utcnow().isoformat()
            }}
        )
        return {"status": "success", "message": f"Entry {gdb_id} routed to ACE Reviewer Pipeline."}
    return {"status": "error", "message": "Unknown action."}
"""

with open(os.path.join(base_dir, "flagging_pipeline.py"), "w", encoding="utf-8") as f:
    f.write(flagging_pipeline_code)

print("flagging_pipeline.py created")
