import os

base_dir = r"C:\Users\meaks\.gemini\antigravity\scratch\ajrasakha-feedback-system\backend\app\services"

# 3. feedback_service.py
feedback_service_code = """from typing import Dict, Any, List
from app.database import get_db

def get_analytics_overview() -> Dict[str, Any]:
    db = get_db()
    
    total_gdb_count = db["gdb_entries"].count_documents({})
    total_feedback_count = db["farmer_feedback"].count_documents({})
    flagged_count = db["flagged_queue"].count_documents({"review_status": "PENDING_AGRI_REVIEW"})
    
    # Calculate overall upvotes and downvotes
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_upvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}},
                "total_downvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}}
            }
        }
    ]
    fb_agg = list(db["farmer_feedback"].aggregate(pipeline))
    upvotes = fb_agg[0]["total_upvotes"] if fb_agg else 0
    downvotes = fb_agg[0]["total_downvotes"] if fb_agg else 0
    overall_ratio = round(upvotes / (upvotes + downvotes), 3) if (upvotes + downvotes) > 0 else 0.0
    
    return {
        "total_gdb_entries": total_gdb_count,
        "total_feedback_captured": total_feedback_count,
        "overall_upvotes": upvotes,
        "overall_downvotes": downvotes,
        "overall_helpful_ratio": overall_ratio,
        "overall_helpful_percentage": round(overall_ratio * 100, 1),
        "total_flagged_for_review": flagged_count,
        "active_threshold": 0.60,
        "min_response_criteria": 10
    }

def get_domain_analytics() -> List[Dict[str, Any]]:
    db = get_db()
    pipeline = [
        {
            "$lookup": {
                "from": "gdb_entries",
                "localField": "gdb_id",
                "foreignField": "_id",
                "as": "gdb"
            }
        },
        {"$unwind": "$gdb"},
        {
            "$group": {
                "_id": "$gdb.domain",
                "total_feedbacks": {"$sum": 1},
                "upvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}},
                "downvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}}
            }
        },
        {"$sort": {"total_feedbacks": -1}}
    ]
    results = list(db["farmer_feedback"].aggregate(pipeline))
    analytics = []
    for r in results:
        tot = r["total_feedbacks"]
        up = r["upvotes"]
        down = r["downvotes"]
        ratio = round(up / tot, 3) if tot > 0 else 0
        analytics.append({
            "domain": r["_id"] or "General Agronomy",
            "total_feedbacks": tot,
            "upvotes": up,
            "downvotes": down,
            "helpful_ratio": ratio,
            "helpful_percentage": round(ratio * 100, 1)
        })
    return analytics

def get_state_analytics() -> List[Dict[str, Any]]:
    db = get_db()
    pipeline = [
        {
            "$group": {
                "_id": "$farmer_state",
                "total_feedbacks": {"$sum": 1},
                "upvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}},
                "downvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}}
            }
        },
        {"$sort": {"total_feedbacks": -1}}
    ]
    results = list(db["farmer_feedback"].aggregate(pipeline))
    analytics = []
    for r in results:
        tot = r["total_feedbacks"]
        up = r["upvotes"]
        down = r["downvotes"]
        ratio = round(up / tot, 3) if tot > 0 else 0
        analytics.append({
            "state": r["_id"] or "Other",
            "total_feedbacks": tot,
            "upvotes": up,
            "downvotes": down,
            "helpful_percentage": round(ratio * 100, 1)
        })
    return analytics

def get_language_analytics() -> List[Dict[str, Any]]:
    db = get_db()
    lang_names = {"hi": "Hindi (हिंदी)", "pa": "Punjabi (ਪੰਜਾਬੀ)", "en": "English", "mr": "Marathi (मराठी)"}
    pipeline = [
        {
            "$group": {
                "_id": "$language",
                "total_feedbacks": {"$sum": 1},
                "upvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}},
                "downvotes": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}}
            }
        },
        {"$sort": {"total_feedbacks": -1}}
    ]
    results = list(db["farmer_feedback"].aggregate(pipeline))
    analytics = []
    for r in results:
        code = r["_id"] or "hi"
        tot = r["total_feedbacks"]
        up = r["upvotes"]
        ratio = round(up / tot, 3) if tot > 0 else 0
        analytics.append({
            "code": code,
            "language_name": lang_names.get(code, code.upper()),
            "total_feedbacks": tot,
            "upvotes": up,
            "downvotes": r["downvotes"],
            "helpful_percentage": round(ratio * 100, 1)
        })
    return analytics
"""

with open(os.path.join(base_dir, "feedback_service.py"), "w", encoding="utf-8") as f:
    f.write(feedback_service_code)

# 4. digest_service.py
digest_service_code = """from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.database import get_db
from app.services.feedback_service import get_analytics_overview, get_domain_analytics, get_state_analytics

def generate_weekly_agri_digest() -> Dict[str, Any]:
    db = get_db()
    overview = get_analytics_overview()
    domain_data = get_domain_analytics()
    state_data = get_state_analytics()
    
    # 5 Lowest rated GDB entries with at least 5 responses
    lowest_entries = list(db["gdb_entries"].find(
        {"metrics.total_feedback": {"$gte": 5}},
        {"_id": 1, "crop": 1, "domain": 1, "question_hi": 1, "question_en": 1, "metrics": 1, "status": 1}
    ).sort("metrics.helpful_ratio", 1).limit(5))
    
    # Format lowest entries
    flagged_digest = []
    for item in lowest_entries:
        m = item.get("metrics", {})
        flagged_digest.append({
            "gdb_id": item["_id"],
            "crop": item.get("crop"),
            "domain": item.get("domain"),
            "question": item.get("question_hi") or item.get("question_en"),
            "helpful_percentage": round(m.get("helpful_ratio", 0) * 100, 1),
            "total_responses": m.get("total_feedback", 0),
            "upvotes": m.get("upvotes", 0),
            "downvotes": m.get("downvotes", 0),
            "status": item.get("status", "ACTIVE")
        })
        
    start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%d %b %Y")
    end_date = datetime.utcnow().strftime("%d %b %Y")
    
    digest_report = {
        "digest_id": f"DIGEST-{datetime.utcnow().strftime('%Y-W%W')}",
        "reporting_period": f"{start_date} – {end_date}",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_feedback": overview["total_feedback_captured"],
            "overall_helpful_pct": overview["overall_helpful_percentage"],
            "flagged_entries_count": overview["total_flagged_for_review"],
            "status_headline": "Requires Attention in Pest & Disease Management" if overview["overall_helpful_percentage"] < 75 else "Stable Quality Index"
        },
        "critical_action_items": [
            "Review GDB-04821 (Wheat Aphid control): 50% approval in Punjab due to complex chemical nomenclature.",
            "Standardize dosage recommendations from metric units (grams/ml per acre) to pump spray units (tanki measurements).",
            "Update regional pesticide advisories for Mustard Aphid in Rajasthan where heatwave conditions render organophosphates less effective."
        ],
        "lowest_performing_gdb_entries": flagged_digest,
        "domain_breakdown": domain_data,
        "state_breakdown": state_data
    }
    
    # Store snapshot in weekly_digests collection
    db["weekly_digests"].update_one(
        {"digest_id": digest_report["digest_id"]},
        {"$set": digest_report},
        upsert=True
    )
    
    return digest_report
"""

with open(os.path.join(base_dir, "digest_service.py"), "w", encoding="utf-8") as f:
    f.write(digest_service_code)

# 5. weather_service.py
weather_service_code = """from typing import Dict, Any, List

def get_imd_agro_alerts() -> Dict[str, Any]:
    \"\"\"
    Provides IMD risk matrix across Indian agro-climatic zones,
    mirroring the user reference images 1, 2, and 4.
    \"\"\"
    zones = [
        {
            "id": "roorkee",
            "city": "Roorkee, Uttarakhand",
            "agro_zone": "Upper Indo-Gangetic Plains",
            "status": "GREEN ALERT",
            "status_desc": "FAVORABLE",
            "temp": 31.7,
            "wind": "6.8 km/h",
            "humidity": "70%",
            "condition": "साफ आसमान / Fair",
            "major_crops": "Sugarcane, Wheat, Mustard",
            "advisory": "Stable and pleasant agricultural weather. Ideal window for regular scheduled irrigation and intercultural operations."
        },
        {
            "id": "shimla",
            "city": "Shimla, Himachal Pradesh",
            "agro_zone": "Himalayan Horticulture Zone",
            "status": "GREEN ALERT",
            "status_desc": "FAVORABLE",
            "temp": 18.2,
            "wind": "14.5 km/h",
            "humidity": "65%",
            "condition": "ठंडा व हल्के बादल / Partly Cloudy",
            "major_crops": "Apple, Stone Fruits, Veggies",
            "advisory": "Maintain orchard hygiene and clear irrigation drainage channels."
        },
        {
            "id": "ludhiana",
            "city": "Ludhiana, Punjab",
            "agro_zone": "North-Western Granary",
            "status": "GREEN ALERT",
            "status_desc": "FAVORABLE",
            "temp": 33.2,
            "wind": "11.2 km/h",
            "humidity": "58%",
            "condition": "धूप खिली / Mostly Sunny",
            "major_crops": "Wheat, Paddy, Cotton",
            "advisory": "Favorable conditions for foliar nutrient sprays. Monitor aphid threshold."
        },
        {
            "id": "bhopal",
            "city": "Bhopal, Madhya Pradesh",
            "agro_zone": "Central Black Soil Belt",
            "status": "GREEN ALERT",
            "status_desc": "FAVORABLE",
            "temp": 28.4,
            "wind": "8.5 km/h",
            "humidity": "62%",
            "condition": "साफ आसमान / Sunny",
            "major_crops": "Soybean, Gram (Chana), Wheat",
            "advisory": "Favorable for sowing preparations and light intercultural hoeing."
        },
        {
            "id": "jaipur",
            "city": "Jaipur, Rajasthan",
            "agro_zone": "Western Semi-Arid Zone",
            "status": "YELLOW ALERT",
            "status_desc": "HEAT/WATCH",
            "temp": 36.4,
            "wind": "16.0 km/h",
            "humidity": "35%",
            "condition": "गर्म व शुष्क / Warm & Dry",
            "major_crops": "Mustard, Bajra, Guar",
            "advisory": "High evaporation risk. Schedule irrigation during evening or night hours."
        },
        {
            "id": "pune",
            "city": "Pune, Maharashtra",
            "agro_zone": "Deccan Plateau & Ghats",
            "status": "GREEN ALERT",
            "status_desc": "FAVORABLE",
            "temp": 29.2,
            "wind": "12.0 km/h",
            "humidity": "68%",
            "condition": "हल्की धूप / Pleasant",
            "major_crops": "Sugarcane, Onion, Grapes",
            "advisory": "Moderate humidity favorable for grape berry development. Spray preventive bio-fungicide."
        }
    ]
    return {"zones": zones, "active_location": zones[0]}

def get_crop_smart_advisory(crop_name: str = "Wheat") -> Dict[str, Any]:
    advisories = {
        "Wheat": {
            "crop_label": "Wheat (गेहूँ)",
            "spray_window": {
                "badge": "SAFE TO SPRAY",
                "title": "Favorable Wind & Zero Rain Risk",
                "details": "Wind speed is 6.8 km/h with dry conditions. Excellent window for WHEAT foliar fungicide/insecticide spray."
            },
            "irrigation": {
                "badge": "IRRIGATION RECOMMENDED",
                "title": "Dry Soil & No Imminent Rain",
                "details": "Clear skies forecasted for the next 48h. Provide light evening irrigation to maintain root zone moisture."
            },
            "pest_index": {
                "badge": "MODERATE SURVEILLANCE",
                "title": "Aphid & Sucking Pest Alert",
                "details": "Current temperature (32°C) favors sucking pests in wheat. Inspect leaf undersides regularly."
            }
        },
        "Paddy": {
            "crop_label": "Paddy / Rice (धान)",
            "spray_window": {
                "badge": "SAFE TO SPRAY",
                "title": "Optimal Morning Application",
                "details": "Spray bio-stimulants or blast preventative fungicides during early morning dew clearance."
            },
            "irrigation": {
                "badge": "MAINTAIN STANDING WATER",
                "title": "Critical Tillering Stage",
                "details": "Ensure 3-5 cm standing water layer is maintained in field plots."
            },
            "pest_index": {
                "badge": "HIGH SURVEILLANCE",
                "title": "Stem Borer & Leaf Folder Watch",
                "details": "Install pheromone traps @ 5 traps/acre for timely threshold detection."
            }
        },
        "Mustard": {
            "crop_label": "Mustard (सरसों)",
            "spray_window": {
                "badge": "CONDITIONAL SPRAY",
                "title": "Spray After 4 PM",
                "details": "Avoid daytime spraying to protect foraging honeybee pollinators in flowering fields."
            },
            "irrigation": {
                "badge": "MOISTURE CONSERVATION",
                "title": "Pod Formation Stage",
                "details": "Apply final light irrigation to aid grain filling."
            },
            "pest_index": {
                "badge": "HIGH SURVEILLANCE",
                "title": "Mustard Aphid Alert",
                "details": "Check top 10 cm of central floral twigs for aphid colonies."
            }
        }
    }
    return advisories.get(crop_name, advisories["Wheat"])
"""

with open(os.path.join(base_dir, "weather_service.py"), "w", encoding="utf-8") as f:
    f.write(weather_service_code)

print("All services created successfully!")
