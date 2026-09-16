import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend"
app_dir = os.path.join(base_dir, "app")
models_dir = os.path.join(app_dir, "models")
services_dir = os.path.join(app_dir, "services")
routers_dir = os.path.join(app_dir, "routers")

for d in [base_dir, app_dir, models_dir, services_dir, routers_dir]:
    os.makedirs(d, exist_ok=True)

# 1. __init__.py files
for d in [app_dir, models_dir, services_dir, routers_dir]:
    with open(os.path.join(d, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("# Package init\n")

# 2. config.py
config_code = '''import os
from pydantic_settings import BaseSettings if False else object

class Settings:
    PROJECT_NAME: str = "AJRASAKHA PS-5 FEEDBACK SUITE"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ajrasakha_db")
    
    # Automated Flagging Thresholds (Configurable by Agri Team)
    FLAG_HELPFUL_THRESHOLD: float = float(os.getenv("FLAG_HELPFUL_THRESHOLD", "0.60")) # < 60%
    FLAG_MIN_RESPONSES: int = int(os.getenv("FLAG_MIN_RESPONSES", "10")) # Minimum 10 responses
    
    # Session Timeout (Minutes for WhatsApp 2-step feedback)
    FEEDBACK_TIMEOUT_MINUTES: int = 120

settings = Settings()
'''

with open(os.path.join(app_dir, "config.py"), "w", encoding="utf-8") as f:
    f.write(config_code)

print("config.py created")
