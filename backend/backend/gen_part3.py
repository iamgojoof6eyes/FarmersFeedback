import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app\services"

# 1. voice_nlp_service.py
voice_nlp_code = """import re
from typing import Dict, Any, Tuple

# Comprehensive multilingual lexicons for Indic sentiment
POSITIVE_INDIC_LEXICON = [
    "काम कर गई", "फायदा हुआ", "माहू खत्म", "कीड़े मर गए", "बढ़िया", "सही सलाह",
    "बहुत अच्छा", "धन्यवाद", "उपयोगी", "ਸਹੀ", "ਲਾਭ ਹੋਇਆ", "ਵਧੀਆ", "ਮਦਦਗਾਰ",
    "helpful", "worked", "effective", "good", "saved my crop", "thanks", "great"
]

NEGATIVE_INDIC_LEXICON = [
    "काम नहीं की", "कीड़े नहीं मरे", "दवा नहीं मिली", "बेकार", "नुकसान हुआ",
    "बहुत कठिन", "समझ नहीं आया", "दुकानदार के पास नहीं थी", "महंगी",
    "ਗਲਤ", "ਕੋਈ ਫਾਇਦਾ ਨਹੀਂ", "ਮਹਿੰਗੀ", "ਸਮਝ ਨਹੀਂ ਆਈ", "ਬੇਕਾਰ",
    "not helpful", "did not work", "ineffective", "bad", "too expensive", "confusing"
]

# Root cause diagnostic patterns
ROOT_CAUSE_PATTERNS = {
    "MEDICINE_UNAVAILABLE_LOCALLY": [
        "दुकान पर नहीं मिली", "बाजार में नहीं है", "दुकानदार बोला नहीं है", "ਮਿਲੀ ਨਹੀਂ",
        "दवा नहीं मिली", "not available", "out of stock", "shop didn't have"
    ],
    "TOO_TECHNICAL": [
        "बहुत कठिन नाम", "समझ नहीं आया", "अंग्रेजी में", "कठिन भाषा", "ਔਖਾ",
        "too technical", "complicated", "confusing", "difficult name"
    ],
    "UNCLEAR_DOSAGE": [
        "कितना पानी मिलाना है", "खुराक स्पष्ट नहीं", "टंकी में कितना डालना", "ਡੋਜ਼",
        "डोज समझ नहीं आई", "unclear dosage", "how much water", "tank quantity"
    ],
    "INEFFECTIVE": [
        "कीड़े नहीं मरे", "बीमारी नहीं रुकी", "असर नहीं हुआ", "ਕੋਈ ਫਾਇਦਾ ਨਹੀਂ",
        "did not cure", "still infected", "ineffective", "waste"
    ]
}

def analyze_voice_feedback(spoken_text: str) -> Dict[str, Any]:
    \"\"\"
    Analyzes an audio transcript from a WhatsApp voice note.
    Returns:
    - rating: 1 (Helpful) or 2 (Not Helpful)
    - confidence: float
    - detected_sentiment: POSITIVE / NEGATIVE / NEUTRAL
    - detected_root_cause: categorized reason if negative
    \"\"\"
    text_lower = spoken_text.lower()
    
    pos_matches = [w for w in POSITIVE_INDIC_LEXICON if w in text_lower]
    neg_matches = [w for w in NEGATIVE_INDIC_LEXICON if w in text_lower]
    
    # Check root causes
    detected_cause = "GENERAL_FEEDBACK"
    for cause, patterns in ROOT_CAUSE_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            detected_cause = cause
            break
            
    if len(neg_matches) > len(pos_matches):
        rating = 2
        sentiment = "NEGATIVE"
        if detected_cause == "GENERAL_FEEDBACK":
            detected_cause = "INEFFECTIVE"
    elif len(pos_matches) > 0:
        rating = 1
        sentiment = "POSITIVE"
        detected_cause = "GENERAL_POSITIVE"
    else:
        # Default fallback based on negation words
        if any(neg in text_lower for neg in ["नहीं", "ਨਾ", "no", "not"]):
            rating = 2
            sentiment = "NEGATIVE"
        else:
            rating = 1
            sentiment = "POSITIVE"
            
    return {
        "transcription": spoken_text,
        "rating": rating,
        "sentiment": sentiment,
        "confidence": 0.92,
        "root_cause": detected_cause,
        "matched_keywords": neg_matches if rating == 2 else pos_matches
    }
"""
with open(os.path.join(base_dir, "voice_nlp_service.py"), "w", encoding="utf-8") as f:
    f.write(voice_nlp_code)

# 2. agro_chrono_service.py
agro_chrono_code = """from datetime import datetime, time, timedelta
from typing import Dict, Any
from app.config import settings

def is_evening_chilling_hours(current_hour: int = None) -> bool:
    \"\"\"
    Determines if local time falls in the farmer evening relaxation window
    (7:00 PM - 9:00 PM / 19:00 - 21:00)
    \"\"\"
    if current_hour is None:
        current_hour = datetime.now().hour
    return settings.CHRONO_LEISURE_START_HOUR <= current_hour <= settings.CHRONO_LEISURE_END_HOUR

def calculate_evening_nudge_time(query_time: datetime = None) -> datetime:
    \"\"\"
    Calculates the target 7:15 PM timestamp for evening re-engagement
    \"\"\"
    now = query_time or datetime.now()
    target_today = now.replace(hour=19, minute=15, second=0, microsecond=0)
    if now.hour >= 19:
        return target_today + timedelta(days=1)
    return target_today

def format_evening_nudge_message(crop_name: str, language: str = "hi") -> str:
    if language == "hi":
        return (
            f"🌙 *शुभ संध्या किसान भाई!* 🙏\n\n"
            f"आज सुबह अजरासखा ने आपके *{crop_name}* के प्रश्न पर सलाह दी थी।\n"
            f"जब आप आराम कर रहे हों, कृपया बताएं: *क्या वह सलाह आपके काम आई?*\n\n"
            f"👇 नीचे दिए बटन पर केवल 1 टैप करें या 1/2 लिखकर भेजें:"
        )
    elif language == "pa":
        return (
            f"🌙 *ਸ਼ਾਮ ਦੀ ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ ਕਿਸਾਨ ਵੀਰੋ!* 🙏\n\n"
            f"ਅੱਜ ਤੁਹਾਡੇ *{crop_name}* ਲਈ ਦਿੱਤੀ ਗਈ ਸਲਾਹ ਕੀ ਲਾਭਦਾਇਕ ਰਹੀ?\n"
            f"ਕਿਰਪਾ ਕਰਕੇ ਹੇਠਾਂ ਦਿੱਤੇ ਬਟਨ 'ਤੇ ਟੈਪ ਕਰੋ:"
        )
    else:
        return (
            f"🌙 *Good Evening Farmer Friend!* 🙏\n\n"
            f"Regarding the advice given earlier for your *{crop_name}* crop:\n"
            f"Was it helpful to your farming operations?\n\n"
            f"👇 Tap one button below to let us know:"
        )
"""
with open(os.path.join(base_dir, "agro_chrono_service.py"), "w", encoding="utf-8") as f:
    f.write(agro_chrono_code)

print("Created voice_nlp_service and agro_chrono_service")
