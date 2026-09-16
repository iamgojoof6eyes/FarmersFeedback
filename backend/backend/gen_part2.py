import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app"

# 1. config.py
config_content = """import os

class Settings:
    PROJECT_NAME: str = "AJRASAKHA PS-5 FEEDBACK SUITE"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api"
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ajrasakha_db")
    
    # Statistical Flagging Pipeline Parameters
    FLAG_HELPFUL_THRESHOLD: float = float(os.getenv("FLAG_HELPFUL_THRESHOLD", "0.60")) # < 60%
    FLAG_MIN_RESPONSES: int = int(os.getenv("FLAG_MIN_RESPONSES", "10")) # Minimum 10 responses
    
    # Agro-Chrono Scheduling Window (Evening Chilling Hours)
    CHRONO_LEISURE_START_HOUR: int = 19 # 7:00 PM
    CHRONO_LEISURE_END_HOUR: int = 21   # 9:00 PM
    FEEDBACK_DAY_TIMEOUT_MINS: int = 120 # 2 hours before scheduling evening nudge

settings = Settings()
"""
with open(os.path.join(base_dir, "config.py"), "w", encoding="utf-8") as f:
    f.write(config_content)

# 2. models/gdb.py
models_gdb = """from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class GDBMetrics(BaseModel):
    total_queries: int = 0
    total_feedback: int = 0
    upvotes: int = 0
    downvotes: int = 0
    helpful_ratio: float = 0.0
    voice_feedback_count: int = 0
    last_feedback_at: Optional[str] = None

class GDBEntryBase(BaseModel):
    crop: str
    domain: str
    sub_domain: Optional[str] = ""
    question_en: str
    question_hi: str
    answer_en: str
    answer_hi: str
    technical_level: str = "Medium"
    status: str = "ACTIVE" # ACTIVE, FLAGGED_REVIEW, IN_REVISION, RE_VALIDATED

class GDBEntry(GDBEntryBase):
    id: str = Field(alias="_id")
    metrics: GDBMetrics = Field(default_factory=GDBMetrics)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        populate_by_name = True
"""
with open(os.path.join(base_dir, "models", "gdb.py"), "w", encoding="utf-8") as f:
    f.write(models_gdb)

# 3. models/feedback.py
models_feedback = """from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class FarmerFeedbackCreate(BaseModel):
    gdb_id: str
    farmer_phone: str = "919876543210"
    farmer_state: str = "Punjab"
    farmer_district: Optional[str] = "Ludhiana"
    language: str = "hi"
    input_channel: str = "WHATSAPP_BUTTON" # WHATSAPP_BUTTON, WHATSAPP_TEXT, WHATSAPP_VOICE
    rating: int # 1 = Helpful, 2 = Not Helpful
    voice_transcription: Optional[str] = None
    root_cause_category: Optional[str] = None # TOO_TECHNICAL, MEDICINE_UNAVAILABLE, UNCLEAR_DOSAGE, INEFFECTIVE, GENERAL_POSITIVE
    query_text: str = ""

class FarmerFeedback(BaseModel):
    id: str = Field(alias="_id")
    gdb_id: str
    farmer_phone_hash: str
    farmer_state: str
    farmer_district: Optional[str] = ""
    language: str
    input_channel: str
    rating: int
    voice_transcription: Optional[str] = None
    root_cause_category: Optional[str] = None
    query_text: str
    scheduled_nudge_delivered: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        populate_by_name = True
"""
with open(os.path.join(base_dir, "models", "feedback.py"), "w", encoding="utf-8") as f:
    f.write(models_feedback)

# 4. models/session.py
models_session = """from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class WhatsAppSimulateRequest(BaseModel):
    phone_number: str = "919876543210"
    message_body: Optional[str] = ""
    farmer_state: str = "Punjab"
    farmer_district: str = "Ludhiana"
    language: str = "hi"
    input_type: str = "TEXT" # "TEXT", "BUTTON_CLICK", "VOICE_NOTE", "ROOT_CAUSE"
    voice_audio_note: Optional[str] = None # simulated spoken words
    button_value: Optional[int] = None # 1 for Yes, 2 for No
    root_cause_selected: Optional[str] = None

class WhatsAppSimulateResponse(BaseModel):
    status: str
    step: str # "ANSWER_DELIVERED", "FEEDBACK_RECORDED", "AWAITING_ROOT_CAUSE", "ROOT_CAUSE_CAPTURED", "SCHEDULED_NUDGE_SENT"
    phone_number: str
    outgoing_messages: List[str]
    quick_reply_buttons: Optional[List[Dict[str, Any]]] = None
    root_cause_options: Optional[List[Dict[str, Any]]] = None
    gdb_id: Optional[str] = None
    feedback_recorded: Optional[Dict[str, Any]] = None
    voice_analysis: Optional[Dict[str, Any]] = None
    session_state: str
"""
with open(os.path.join(base_dir, "models", "session.py"), "w", encoding="utf-8") as f:
    f.write(models_session)

print("Generated config.py and all models.")
