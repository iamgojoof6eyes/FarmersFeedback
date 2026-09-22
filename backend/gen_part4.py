import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app\services"

# 3. flagging_pipeline.py
flagging_code = """from datetime import datetime
from typing import Dict, Any, Optional
import logging
from app.config import settings
from app.database import get_db

logger = logging.getLogger("ajrasakha.flagging")

def evaluate_and_flag_gdb(gdb_id: str) -> Optional[Dict[str, Any]]:
    \"\"\"
    Evaluates whether a GDB entry has dropped below the quality threshold:
    Condition: total_feedback >= FLAG_MIN_RESPONSES (10) AND helpful_ratio < 0.60
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
    
    # Flagging Rule
    is_failing = (total_fb >= settings.FLAG_MIN_RESPONSES) and (helpful_ratio < settings.FLAG_HELPFUL_THRESHOLD)
    
    if is_failing:
        # Aggregate root cause feedback
        causes = list(db["farmer_feedback"].find(
            {"gdb_id": gdb_id, "rating": 2},
            {"root_cause_category": 1, "farmer_state": 1}
        ))
        
        cause_counts = {}
        states = []
        for c in causes:
            cat = c.get("root_cause_category") or "TOO_TECHNICAL"
            cause_counts[cat] = cause_counts.get(cat, 0) + 1
            if c.get("farmer_state"):
                states.append(c["farmer_state"])
                
        tot_neg = len(causes) or 1
        cause_percentages = {k: f"{round((v/tot_neg)*100)}%" for k, v in cause_counts.items()}
        most_affected_state = max(set(states), key=states.count) if states else "Punjab"
        
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
            "root_cause_breakdown": cause_percentages,
            "flag_reason": f"Helpfulness ({int(helpful_ratio*100)}%) dropped below {int(settings.FLAG_HELPFUL_THRESHOLD*100)}% across {total_fb} farmer responses.",
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
        return flag_data
    return None

def resolve_flagged_entry(gdb_id: str, revised_answer_hi: str, revised_answer_en: str, reviewer_note: str, action: str):
    db = get_db()
    if action == "REVISE_AND_REVALIDATE":
        db["gdb_entries"].update_one(
            {"_id": gdb_id},
            {"$set": {
                "answer_hi": revised_answer_hi,
                "answer_en": revised_answer_en,
                "status": "RE_VALIDATED",
                "technical_level": "Simple",
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
    f.write(flagging_code)

# 4. whatsapp_service.py
whatsapp_service_code = """import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import re
from app.config import settings
from app.database import get_db
from app.services.flagging_pipeline import evaluate_and_flag_gdb
from app.services.voice_nlp_service import analyze_voice_feedback
from app.services.agro_chrono_service import format_evening_nudge_message

YES_TOKENS = {"1", "yes", "ha", "haan", "sahi", "helpful", "theek", "shukriya", "???", "??", "?????", "???", "??????", "???", "???", "?????", "???"}
NO_TOKENS = {"2", "no", "nahi", "galat", "unhelpful", "kharab", "bekar", "????", "??", "???", "????????", "????", "???"}

def get_farmer_session(phone_number: str, state: str = "Punjab", language: str = "hi") -> Dict[str, Any]:
    db = get_db()
    session = db["farmer_sessions"].find_one({"phone_number": phone_number})
    if not session:
        session = {
            "phone_number": phone_number,
            "current_state": "IDLE",
            "active_gdb_id": None,
            "last_query": None,
            "crop_in_context": "Wheat",
            "language_preference": language,
            "farmer_state": state,
            "farmer_district": "Ludhiana" if state == "Punjab" else "Roorkee",
            "query_delivered_at": None,
            "nudge_scheduled": False,
            "updated_at": datetime.utcnow().isoformat()
        }
        db["farmer_sessions"].insert_one(session)
    return session

def update_session(phone_number: str, update_data: Dict[str, Any]):
    db = get_db()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    db["farmer_sessions"].update_one({"phone_number": phone_number}, {"$set": update_data})

def find_best_gdb_match(query: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    q_norm = query.lower()
    words = [re.escape(w) for w in q_norm.split() if len(w) > 2]
    if words:
        pattern = "|".join(words)
        match = db["gdb_entries"].find_one({
            "$or": [
                {"question_hi": {"$regex": pattern, "$options": "i"}},
                {"question_en": {"$regex": pattern, "$options": "i"}},
                {"crop": {"$regex": pattern, "$options": "i"}},
                {"sub_domain": {"$regex": pattern, "$options": "i"}},
                {"answer_hi": {"$regex": pattern, "$options": "i"}}
            ]
        })
        if match:
            return match
    return db["gdb_entries"].find_one({"status": "ACTIVE"})

def process_farmer_interaction(
    phone_number: str,
    message_body: str = "",
    farmer_state: str = "Punjab",
    language: str = "hi",
    input_type: str = "TEXT", # "TEXT", "BUTTON_CLICK", "VOICE_NOTE", "ROOT_CAUSE", "TRIGGER_NUDGE"
    voice_audio_note: Optional[str] = None,
    button_value: Optional[int] = None,
    root_cause_selected: Optional[str] = None
) -> Dict[str, Any]:
    db = get_db()
    session = get_farmer_session(phone_number, farmer_state, language)
    current_state = session.get("current_state", "IDLE")
    active_gdb_id = session.get("active_gdb_id")
    crop_name = session.get("crop_in_context", "?????")
    phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()[:16]
    
    # -------------------------------------------------------------
    # Action 1: Trigger Simulated Evening Scheduled Nudge
    # -------------------------------------------------------------
    if input_type == "TRIGGER_NUDGE":
        nudge_text = format_evening_nudge_message(crop_name, language)
        buttons = [
            {"id": "btn_yes", "title": "?? ???, ?????? ???", "value": 1},
            {"id": "btn_no", "title": "?? ????, ????? ?????", "value": 2}
        ]
        update_session(phone_number, {"current_state": "AWAITING_FEEDBACK", "nudge_scheduled": True})
        return {
            "status": "success",
            "step": "SCHEDULED_NUDGE_SENT",
            "phone_number": phone_number,
            "outgoing_messages": [nudge_text],
            "quick_reply_buttons": buttons,
            "gdb_id": active_gdb_id,
            "session_state": "AWAITING_FEEDBACK"
        }

    # -------------------------------------------------------------
    # Action 2: Handling Root Cause Selection on Downvote
    # -------------------------------------------------------------
    if input_type == "ROOT_CAUSE" or (current_state == "AWAITING_ROOT_CAUSE" and root_cause_selected):
        db["farmer_feedback"].update_one(
            {"gdb_id": active_gdb_id, "farmer_phone_hash": phone_hash},
            {"$set": {"root_cause_category": root_cause_selected}},
            sort=[("timestamp", -1)]
        )
        evaluate_and_flag_gdb(active_gdb_id)
        update_session(phone_number, {"current_state": "IDLE", "active_gdb_id": None})
        
        ack = (
            "??????????? ???? ?? ?? ?? ??! ????\n"
            "???? ???? ?????? ???? ?? ???? ?? ??? ?? ???? ??? ????? ???? ????????? (ACE Reviewer Pipeline) ??? ????? ??????????"
            if language == "hi" else
            "Thank you! Your specific feedback has been shared with the ACE Agronomy Board for immediate revision. ??"
        )
        return {
            "status": "success",
            "step": "ROOT_CAUSE_CAPTURED",
            "phone_number": phone_number,
            "outgoing_messages": [ack],
            "gdb_id": active_gdb_id,
            "session_state": "IDLE"
        }

    # -------------------------------------------------------------
    # Action 3: Voice Note Ingestion
    # -------------------------------------------------------------
    if input_type == "VOICE_NOTE" and voice_audio_note:
        analysis = analyze_voice_feedback(voice_audio_note)
        rating = analysis["rating"]
        root_cause = analysis["root_cause"]
        
        fb_id = f"FB-VOICE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{phone_hash[:4]}"
        db["farmer_feedback"].insert_one({
            "_id": fb_id,
            "gdb_id": active_gdb_id or "GDB-04821",
            "farmer_phone_hash": phone_hash,
            "farmer_state": farmer_state,
            "farmer_district": session.get("farmer_district", "Ludhiana"),
            "language": language,
            "input_channel": "WHATSAPP_VOICE",
            "rating": rating,
            "voice_transcription": voice_audio_note,
            "root_cause_category": root_cause,
            "query_text": session.get("last_query", "Voice Query"),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        vote_field = "metrics.upvotes" if rating == 1 else "metrics.downvotes"
        db["gdb_entries"].update_one(
            {"_id": active_gdb_id or "GDB-04821"},
            {"$inc": {vote_field: 1, "metrics.voice_feedback_count": 1}}
        )
        flag_info = evaluate_and_flag_gdb(active_gdb_id or "GDB-04821")
        update_session(phone_number, {"current_state": "IDLE", "active_gdb_id": None})
        
        reply_msg = (
            f"??? *???? ????? ???? ??:* \"{voice_audio_note}\"\n\n"
            f"???????! ???? ??????????? ???? ?? ?? ?? ??? ({'?? ??????' if rating == 1 else '?? ????? ?????'})\n"
            "?? *????? ????????:* ???? ??????????? ?? ???? ??????? ?? ???? 500+ ????? ?????? ?? ????? ???? ??????!"
            if language == "hi" else
            f"??? *Voice Note Processed:* \"{voice_audio_note}\"\nFeedback recorded successfully! ??"
        )
        return {
            "status": "success",
            "step": "FEEDBACK_RECORDED",
            "phone_number": phone_number,
            "outgoing_messages": [reply_msg],
            "gdb_id": active_gdb_id,
            "voice_analysis": analysis,
            "flagged_info": flag_info,
            "session_state": "IDLE"
        }

    # -------------------------------------------------------------
    # Action 4: Rating Button Click or Text '1'/'2'
    # -------------------------------------------------------------
    cleaned = message_body.strip().lower()
    is_voting = (
        input_type == "BUTTON_CLICK" or
        cleaned in YES_TOKENS or
        cleaned in NO_TOKENS or
        button_value in [1, 2]
    )
    
    if current_state == "AWAITING_FEEDBACK" and is_voting and active_gdb_id:
        if button_value:
            rating = button_value
        else:
            rating = 1 if cleaned in YES_TOKENS else 2
            
        fb_id = f"FB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{phone_hash[:4]}"
        db["farmer_feedback"].insert_one({
            "_id": fb_id,
            "gdb_id": active_gdb_id,
            "farmer_phone_hash": phone_hash,
            "farmer_state": farmer_state,
            "farmer_district": session.get("farmer_district", "General"),
            "language": language,
            "input_channel": "WHATSAPP_BUTTON" if input_type == "BUTTON_CLICK" else "WHATSAPP_TEXT",
            "rating": rating,
            "root_cause_category": "GENERAL_POSITIVE" if rating == 1 else "AWAITING_REASON",
            "query_text": session.get("last_query", "WhatsApp query"),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        vote_field = "metrics.upvotes" if rating == 1 else "metrics.downvotes"
        db["gdb_entries"].update_one(
            {"_id": active_gdb_id},
            {"$inc": {vote_field: 1, "metrics.total_queries": 1}}
        )
        flag_info = evaluate_and_flag_gdb(active_gdb_id)
        
        if rating == 2:
            # Trigger 1-Tap Root Cause Follow-up
            update_session(phone_number, {"current_state": "AWAITING_ROOT_CAUSE"})
            root_cause_msg = (
                "????? ?? ??? ????? ????? ???? ????? (1 ??? ????):"
                if language == "hi" else "Please select the primary reason for improvement:"
            )
            options = [
                {"id": "TOO_TECHNICAL", "label": "?? ???? ???? ???? / ???????? ????"},
                {"id": "MEDICINE_UNAVAILABLE_LOCALLY", "label": "?? ?????/????? ?? ??? ???? ????"},
                {"id": "UNCLEAR_DOSAGE", "label": "?? ???? ? ??? ?? ?????? ???????"},
                {"id": "INEFFECTIVE", "label": "?? ??? ?? ??????/??? ???? ????"}
            ]
            return {
                "status": "success",
                "step": "AWAITING_ROOT_CAUSE",
                "phone_number": phone_number,
                "outgoing_messages": [root_cause_msg],
                "root_cause_options": options,
                "gdb_id": active_gdb_id,
                "session_state": "AWAITING_ROOT_CAUSE"
            }
        else:
            update_session(phone_number, {"current_state": "IDLE", "active_gdb_id": None})
            ack = (
                "???????! ???? ??????????? ???? ?? ?? ?? ??? ????\n"
                "?? *????? ????????:* ???? ?????? ?? ???? ???? ?? 500+ ????? ?????? ?? ????? ???? ???????"
                if language == "hi" else
                "Thank you! Your feedback helps 500+ fellow farmers receive validated agronomic advice. ????"
            )
            return {
                "status": "success",
                "step": "FEEDBACK_RECORDED",
                "phone_number": phone_number,
                "outgoing_messages": [ack],
                "gdb_id": active_gdb_id,
                "flagged_info": flag_info,
                "session_state": "IDLE"
            }

    # -------------------------------------------------------------
    # Action 5: Initial Farmer Question
    # -------------------------------------------------------------
    gdb_entry = find_best_gdb_match(message_body)
    matched_id = gdb_entry["_id"]
    crop = gdb_entry.get("crop", "?????")
    
    answer_text = (
        f"?? *??????? ???? ???? (GDB: {matched_id})* ??\n\n"
        f"{gdb_entry.get('answer_hi', gdb_entry.get('answer_en'))}"
    )
    prompt_text = "? *???? ?? ??????? ???? ??? ?????? ???*"
    
    quick_buttons = [
        {"id": "btn_yes", "title": "?? ???, ?????? ??", "value": 1},
        {"id": "btn_no", "title": "?? ????, ????? ?????", "value": 2}
    ]
    
    update_session(phone_number, {
        "current_state": "AWAITING_FEEDBACK",
        "active_gdb_id": matched_id,
        "crop_in_context": crop,
        "last_query": message_body,
        "query_delivered_at": datetime.utcnow().isoformat(),
        "nudge_scheduled": False
    })
    
    db["gdb_entries"].update_one({"_id": matched_id}, {"$inc": {"metrics.total_queries": 1}})
    
    return {
        "status": "success",
        "step": "ANSWER_DELIVERED",
        "phone_number": phone_number,
        "outgoing_messages": [answer_text, prompt_text],
        "quick_reply_buttons": quick_buttons,
        "gdb_id": matched_id,
        "session_state": "AWAITING_FEEDBACK"
    }
"""
with open(os.path.join(base_dir, "whatsapp_service.py"), "w", encoding="utf-8") as f:
    f.write(whatsapp_service_code)

print("Created flagging_pipeline.py and enhanced whatsapp_service.py")
