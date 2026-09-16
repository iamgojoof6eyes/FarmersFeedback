from fastapi import APIRouter
from app.services.digest_service import generate_weekly_agri_digest

router = APIRouter(prefix="/digest", tags=["Weekly Agri Digest"])

@router.get("/weekly")
def get_digest():
    return generate_weekly_agri_digest()
