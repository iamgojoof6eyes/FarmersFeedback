import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app"

# 1. models/gdb.py
models_gdb = """from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class GDBMetrics(BaseModel):
    total_queries: int = 0
    total_feedback: int = 0
    upvotes: int = 0
    downvotes: int = 0
    helpful_ratio: float = 0.0
    last_feedback_at: Optional[str] = None

class GDBEntryBase(BaseModel):
    crop: str
    domain: str
    sub_domain: Optional[str] = ""
    question_en: str
    question_hi: str
    answer_en: str
    answer_hi: str
    technical_level: str = "Medium" # "Simple", "Medium", "High"
    status: str = "ACTIVE" # "ACTIVE", "FLAGGED_REVIEW", "IN_REVISION", "RE_VALIDATED"

class GDBEntry(GDBEntryBase):
    id: str = Field(alias="_id")
    metrics: GDBMetrics = Field(default_factory=GDBMetrics)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        populate_by_name = True

class GDBUpdate(BaseModel):
    question_en: Optional[str] = None
    question_hi: Optional[str] = None
    answer_en: Optional[str] = None
    answer_hi: Optional[str] = None
    technical_level: Optional[str] = None
    status: Optional[str] = None
"""

with open(os.path.join(base_dir, "models", "gdb.py"), "w", encoding="utf-8") as f:
    f.write(models_gdb)

# 2. models/feedback.py
models_feedback = """from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class FarmerFeedbackCreate(BaseModel):
    gdb_id: str
    farmer_phone: str = "919876543210"
    farmer_state: str = "Punjab"
    farmer_district: Optional[str] = "Ludhiana"
    language: str = "hi"
    query_text: str
    rating: int # 1 = Yes (Helpful), 2 = No (Not Helpful)
    feedback_reason: Optional[str] = None
    channel: str = "WHATSAPP"

class FarmerFeedback(BaseModel):
    id: str = Field(alias="_id")
    gdb_id: str
    farmer_phone_hash: str
    farmer_state: str
    farmer_district: Optional[str] = ""
    language: str
    query_text: str
    rating: int
    feedback_reason: Optional[str] = None
    channel: str = "WHATSAPP"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        populate_by_name = True
"""

with open(os.path.join(base_dir, "models", "feedback.py"), "w", encoding="utf-8") as f:
    f.write(models_feedback)

# 3. models/session.py
models_session = """from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class WhatsAppSession(BaseModel):
    phone_number: str
    current_state: str = "IDLE" # "IDLE", "AWAITING_FEEDBACK"
    active_gdb_id: Optional[str] = None
    last_query: Optional[str] = None
    last_answer: Optional[str] = None
    language_preference: str = "hi"
    farmer_state: str = "Punjab"
    farmer_district: str = "Ludhiana"
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[datetime] = None

class WhatsAppSimulateRequest(BaseModel):
    phone_number: str = "919876543210"
    message_body: str
    farmer_state: str = "Punjab"
    farmer_district: str = "Ludhiana"
    language: str = "hi"

class WhatsAppSimulateResponse(BaseModel):
    status: str
    step: str # "ANSWER_DELIVERED", "FEEDBACK_RECORDED", "NEW_QUERY"
    phone_number: str
    outgoing_messages: list[str]
    gdb_id: Optional[str] = None
    feedback_recorded: Optional[Dict[str, Any]] = None
    session_state: str
"""

with open(os.path.join(base_dir, "models", "session.py"), "w", encoding="utf-8") as f:
    f.write(models_session)

print("Models created successfully!")
