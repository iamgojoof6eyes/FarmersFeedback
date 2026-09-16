import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app\services"

# 2. whatsapp_service.py
whatsapp_service_code = """import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import re
from app.config import settings
from app.database import get_db
from app.services.flagging_pipeline import evaluate_and_flag_gdb

# Multi-lingual affirmation and negation token dictionaries
YES_TOKENS = {
    "1", "1.", "yes", "ha", "haan", "sahi", "helpful", "theek", "shukriya",
    "हाँ", "हा", "हाँजी", "सही", "उपयोगी", "काम", "ਹਾਂ", "ਹਾਂਜੀ", "ਠੀਕ"
}

NO_TOKENS = {
    "2", "2.", "no", "nahi", "galat", "unhelpful", "kharab", "bekar",
    "नहीं", "ना", "गलत", "अनुपयोगी", "समझ नहीं आया", "ਨਹੀਂ", "ਗਲਤ"
}

def normalize_text(text: str) -> str:
    return text.strip().lower()

def get_farmer_session(phone_number: str, state: str = "Punjab", language: str = "hi") -> Dict[str, Any]:
    db = get_db()
    session = db["farmer_sessions"].find_one({"phone_number": phone_number})
    if not session:
        session = {
            "phone_number": phone_number,
            "current_state": "IDLE",
            "active_gdb_id": None,
            "last_query": None,
            "last_answer": None,
            "language_preference": language,
            "farmer_state": state,
            "farmer_district": "Ludhiana" if state == "Punjab" else "Roorkee",
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": datetime.utcnow() + timedelta(minutes=settings.FEEDBACK_TIMEOUT_MINUTES)
        }
        db["farmer_sessions"].insert_one(session)
    return session

def update_session(phone_number: str, update_data: Dict[str, Any]):
    db = get_db()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    update_data["expires_at"] = datetime.utcnow() + timedelta(minutes=settings.FEEDBACK_TIMEOUT_MINUTES)
    db["farmer_sessions"].update_one(
        {"phone_number": phone_number},
        {"$set": update_data}
    )

def find_best_gdb_match(query: str, crop_context: Optional[str] = None) -> Optional[Dict[str, Any]]:
    \"\"\"
    Performs keyword & regex matching across questions and crops in GDB
    \"\"\"
    db = get_db()
    q_norm = query.lower()
    
    # 1. Search for keyword matches
    regex_terms = [re.escape(word) for word in q_norm.split() if len(word) > 2]
    if regex_terms:
        pattern = "|".join(regex_terms)
        query_filter = {
            "$or": [
                {"question_hi": {"$regex": pattern, "$options": "i"}},
                {"question_en": {"$regex": pattern, "$options": "i"}},
                {"crop": {"$regex": pattern, "$options": "i"}},
                {"sub_domain": {"$regex": pattern, "$options": "i"}},
                {"answer_hi": {"$regex": pattern, "$options": "i"}}
            ]
        }
        match = db["gdb_entries"].find_one(query_filter)
        if match:
            return match
            
    # Fallback to any active GDB entry
    return db["gdb_entries"].find_one({"status": "ACTIVE"})

def process_farmer_message(
    phone_number: str,
    message_body: str,
    farmer_state: str = "Punjab",
    language: str = "hi",
    gdb_hint_id: Optional[str] = None
) -> Dict[str, Any]:
    \"\"\"
    Two-step WhatsApp state machine:
    Step 1: Farmer asks question -> System delivers answer + follow-up prompt:
            'क्या यह उत्तर आपके लिए उपयोगी था? हाँ के लिए 1, नहीं के लिए 2 भेजें'
    Step 2: Farmer replies 1 or 2 -> Feedback captured, GDB metrics updated,
            automated flagging checked.
    \"\"\"
    db = get_db()
    session = get_farmer_session(phone_number, farmer_state, language)
    cleaned_input = normalize_text(message_body)
    outgoing_messages: List[str] = []
    
    current_state = session.get("current_state", "IDLE")
    active_gdb_id = session.get("active_gdb_id")
    
    # Check if this is a feedback response to an active question
    is_feedback_turn = (current_state == "AWAITING_FEEDBACK" and active_gdb_id is not None)
    is_explicit_vote = cleaned_input in YES_TOKENS or cleaned_input in NO_TOKENS
    
    if is_feedback_turn and is_explicit_vote:
        # Step 2: Record Feedback
        rating = 1 if cleaned_input in YES_TOKENS else 2
        phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()[:16]
        
        feedback_id = f"FB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{phone_hash[:6]}"
        feedback_doc = {
            "_id": feedback_id,
            "gdb_id": active_gdb_id,
            "farmer_phone_hash": phone_hash,
            "farmer_state": session.get("farmer_state", farmer_state),
            "farmer_district": session.get("farmer_district", "General"),
            "language": session.get("language_preference", language),
            "query_text": session.get("last_query", "WhatsApp query"),
            "rating": rating,
            "feedback_reason": "Too technical / difficult dosage" if rating == 2 else "Clear and actionable",
            "channel": "WHATSAPP",
            "timestamp": datetime.utcnow().isoformat()
        }
        db["farmer_feedback"].insert_one(feedback_doc)
        
        # Increment GDB metrics
        vote_field = "metrics.upvotes" if rating == 1 else "metrics.downvotes"
        db["gdb_entries"].update_one(
            {"_id": active_gdb_id},
            {"$inc": {vote_field: 1, "metrics.total_queries": 1}}
        )
        
        # Evaluate automated quality flagging rule
        flag_result = evaluate_and_flag_gdb(active_gdb_id)
        
        # Acknowledge back to farmer
        if rating == 1:
            reply_msg = (
                "धन्यवाद! आपकी प्रतिक्रिया दर्ज कर ली गई है। 🙏🌾\n"
                "अजरासखा (AjraSakha) सदैव आपके साथ है। यदि कोई अन्य प्रश्न हो तो अवश्य पूछें।"
                if language == "hi" else
                "ਧੰਨਵਾਦ! ਤੁਹਾਡੀ ਫੀਡਬੈਕ ਦਰਜ ਕਰ ਲਈ ਗਈ ਹੈ। 🙏🌾\nਅਜਰਾਸਖਾ ਹਮੇਸ਼ਾ ਤੁਹਾਡੇ ਨਾਲ ਹੈ।"
                if language == "pa" else
                "Thank you! Your feedback has been recorded. 🙏🌾\nAjraSakha is always here to assist your farming."
            )
        else:
            reply_msg = (
                "प्रतिक्रिया के लिए धन्यवाद। 🌾\n"
                "हम इस उत्तर को हमारे कृषि वैज्ञानिकों (ACE Reviewer Pipeline) के पास सुधार हेतु भेज रहे हैं ताकि अगली बार आपको अधिक सटीक व सरल सलाह मिल सके।"
                if language == "hi" else
                "ਫੀਡਬੈਕ ਲਈ ਧੰਨਵਾਦ। ਅਸੀਂ ਇਸ ਜਵਾਬ ਨੂੰ ਖੇਤੀਬਾੜੀ ਮਾਹਿਰਾਂ ਨੂੰ ਸੁਧਾਰ ਲਈ ਭੇਜ ਰਹੇ ਹਾਂ।"
                if language == "pa" else
                "Thank you for the feedback. 🌾\nWe have flagged this answer for review by our agricultural scientists to make it clearer and more practical."
            )
            
        outgoing_messages.append(reply_msg)
        
        # Reset session
        update_session(phone_number, {
            "current_state": "IDLE",
            "active_gdb_id": None
        })
        
        return {
            "status": "success",
            "step": "FEEDBACK_RECORDED",
            "phone_number": phone_number,
            "outgoing_messages": outgoing_messages,
            "gdb_id": active_gdb_id,
            "feedback_recorded": feedback_doc,
            "flagged_info": flag_result,
            "session_state": "IDLE"
        }
        
    else:
        # Step 1: New Agricultural Question
        if gdb_hint_id:
            gdb_entry = db["gdb_entries"].find_one({"_id": gdb_hint_id})
        else:
            gdb_entry = find_best_gdb_match(message_body)
            
        if not gdb_entry:
            return {
                "status": "not_found",
                "step": "NO_MATCH",
                "phone_number": phone_number,
                "outgoing_messages": ["क्षमा करें, इस विषय पर अभी प्रमाणित जानकारी उपलब्ध नहीं है। कृपया कृषि विज्ञान केंद्र से संपर्क करें।"],
                "session_state": "IDLE"
            }
            
        matched_gdb_id = gdb_entry["_id"]
        
        # Construct Answer Message
        if language == "hi":
            answer_text = f"🌾 *अजरासखा कृषि सलाह (GDB: {matched_gdb_id})* 🌾\n\n{gdb_entry.get('answer_hi', gdb_entry.get('answer_en'))}"
            followup_prompt = (
                "\n\n━━━━━━━━━━━━━━━━━━━━\n"
                "❓ *क्या यह उत्तर आपके लिए उपयोगी था?*\n"
                "• हाँ के लिए *1* भेजें\n"
                "• नहीं के लिए *2* भेजें\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
        elif language == "pa":
            answer_text = f"🌾 *ਅਜਰਾਸਖਾ ਖੇਤੀ ਸਲਾਹ (GDB: {matched_gdb_id})* 🌾\n\n{gdb_entry.get('answer_hi', gdb_entry.get('answer_en'))}"
            followup_prompt = (
                "\n\n━━━━━━━━━━━━━━━━━━━━\n"
                "❓ *ਕੀ ਇਹ ਜਾਣਕਾਰੀ ਲਾਭਦਾਇਕ ਸੀ?*\n"
                "• ਹਾਂ ਲਈ *1* ਭੇਜੋ\n"
                "• ਨਹੀਂ ਲਈ *2* ਭੇਜੋ\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            answer_text = f"🌾 *AjraSakha Expert Advisory (GDB: {matched_gdb_id})* 🌾\n\n{gdb_entry.get('answer_en', gdb_entry.get('answer_hi'))}"
            followup_prompt = (
                "\n\n━━━━━━━━━━━━━━━━━━━━\n"
                "❓ *Was this helpful?*\n"
                "• Reply *1* for Yes\n"
                "• Reply *2* for No\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            
        full_response = answer_text + followup_prompt
        outgoing_messages.append(full_response)
        
        # Update Session State to AWAITING_FEEDBACK
        update_session(phone_number, {
            "current_state": "AWAITING_FEEDBACK",
            "active_gdb_id": matched_gdb_id,
            "last_query": message_body,
            "last_answer": answer_text,
            "language_preference": language,
            "farmer_state": farmer_state
        })
        
        # Increment total queries on GDB entry
        db["gdb_entries"].update_one(
            {"_id": matched_gdb_id},
            {"$inc": {"metrics.total_queries": 1}}
        )
        
        return {
            "status": "success",
            "step": "ANSWER_DELIVERED",
            "phone_number": phone_number,
            "outgoing_messages": outgoing_messages,
            "gdb_id": matched_gdb_id,
            "session_state": "AWAITING_FEEDBACK"
        }
"""

with open(os.path.join(base_dir, "whatsapp_service.py"), "w", encoding="utf-8") as f:
    f.write(whatsapp_service_code)

print("whatsapp_service.py created")
