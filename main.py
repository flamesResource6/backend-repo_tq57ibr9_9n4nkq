import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import User as UserSchema, Business as BusinessSchema, Visit as VisitSchema, Impact as ImpactSchema
from bson import ObjectId

app = FastAPI(title="Terra Tranquil API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Utilities
# -----------------------------

def to_obj_id(id_str: str):
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def business_doc_to_response(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


# -----------------------------
# Schemas for requests
# -----------------------------
class BusinessCreate(BaseModel):
    name: str
    category: str
    location: str
    website: Optional[str] = None
    description: Optional[str] = None
    eco_checks: List[bool] = Field(default_factory=list)
    logo_url: Optional[str] = None

class VisitCreate(BaseModel):
    user_id: str
    username: str
    business_id: str


# -----------------------------
# Seeds
# -----------------------------
SAMPLE_BUSINESSES = [
    {
        "name": "Leaf & Latte Café",
        "category": "Cafés",
        "location": "Downtown",
        "website": "https://leaflatte.example",
        "description": "Plant-forward menu, compostable packaging, local roasters.",
        "eco_checks": [True, True, True, True, False],
        "logo_url": None,
        "eco_score": 92,
        "hero_image": None,
    },
    {
        "name": "Green Grove Grocers",
        "category": "Groceries",
        "location": "Riverside",
        "website": "https://greengrove.example",
        "description": "Organic produce, refill station, zero-waste aisle.",
        "eco_checks": [True, True, True, True, True],
        "logo_url": None,
        "eco_score": 88,
        "hero_image": None,
    },
    {
        "name": "Willow Wellness Studio",
        "category": "Wellness",
        "location": "Old Town",
        "website": "https://willowwellness.example",
        "description": "Mindful movement with eco mats and clean air systems.",
        "eco_checks": [True, False, True, True, True],
        "logo_url": None,
        "eco_score": 84,
        "hero_image": None,
    },
    {
        "name": "Harvest Hill Farm",
        "category": "Farms",
        "location": "Foothills",
        "website": "https://harvesthill.example",
        "description": "Regenerative agriculture and weekly harvest boxes.",
        "eco_checks": [True, True, True, False, True],
        "logo_url": None,
        "eco_score": 95,
        "hero_image": None,
    },
    {
        "name": "Local Loop Shop",
        "category": "Local Shops",
        "location": "Market Street",
        "website": "https://localloop.example",
        "description": "Circular design goods and repair-friendly products.",
        "eco_checks": [True, True, False, True, True],
        "logo_url": None,
        "eco_score": 90,
        "hero_image": None,
    },
]

@app.on_event("startup")
def seed_data():
    if db is None:
        return
    if db.business.count_documents({}) == 0:
        for b in SAMPLE_BUSINESSES:
            create_document("business", BusinessSchema(**b))


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def root():
    return {"name": "Terra Tranquil API", "status": "ok"}

@app.get("/schema")
def get_schema_info():
    # Minimal schema info for the viewer
    return {
        "collections": ["user", "business", "visit", "impact"],
    }

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Directory
@app.get("/api/businesses")
def list_businesses(search: Optional[str] = None, category: Optional[str] = None):
    if db is None:
        return []
    q = {}
    if category and category.lower() != "all":
        q["category"] = category
    if search:
        q["name"] = {"$regex": search, "$options": "i"}
    docs = db.business.find(q).limit(100)
    return [business_doc_to_response(d) for d in docs]

@app.get("/api/businesses/{business_id}")
def get_business(business_id: str):
    if db is None:
        raise HTTPException(500, "Database not available")
    d = db.business.find_one({"_id": to_obj_id(business_id)})
    if not d:
        raise HTTPException(404, "Business not found")
    return business_doc_to_response(d)

@app.post("/api/businesses")
def register_business(payload: BusinessCreate):
    data = payload.model_dump()
    # default eco_score if checklist present
    checks = data.get("eco_checks", [])
    if checks:
        data["eco_score"] = int(60 + sum(1 for c in checks if c) * 8)
    bid = create_document("business", BusinessSchema(**data))
    d = db.business.find_one({"_id": ObjectId(bid)})
    return business_doc_to_response(d)

# Visits & Impact
@app.get("/api/users/{user_id}/impact")
def get_impact(user_id: str, username: Optional[str] = None):
    if db is None:
        return ImpactSchema(user_id=user_id, username=username or "Guest").model_dump()
    doc = db.impact.find_one({"user_id": user_id})
    if not doc:
        impact = ImpactSchema(user_id=user_id, username=username or "Guest")
        create_document("impact", impact)
        return impact.model_dump()
    doc.pop("_id", None)
    return doc

@app.get("/api/users/{user_id}/visits")
def get_user_visits(user_id: str):
    if db is None:
        return []
    visits = db.visit.find({"user_id": user_id}).sort("created_at", -1).limit(100)
    out = []
    for v in visits:
        v["id"] = str(v.pop("_id"))
        out.append(v)
    return out

@app.post("/api/visits")
def log_visit(payload: VisitCreate):
    if db is None:
        raise HTTPException(500, "Database not available")
    # verify business exists
    bdoc = db.business.find_one({"_id": to_obj_id(payload.business_id)})
    if not bdoc:
        raise HTTPException(404, "Business not found")
    visit = VisitSchema(
        user_id=payload.user_id,
        business_id=payload.business_id,
        business_name=bdoc.get("name"),
        category=bdoc.get("category"),
        location=bdoc.get("location"),
        eco_points=10,
    )
    create_document("visit", visit)
    # upsert impact counters
    inc = {
        "$setOnInsert": {
            "user_id": payload.user_id,
            "username": payload.username,
        },
        "$inc": {
            "visits": 1,
            "eco_points": visit.eco_points,
            "community_impact": 1,
        }
    }
    db.impact.update_one({"user_id": payload.user_id}, inc, upsert=True)
    # recompute terra level (simple tiers)
    imp = db.impact.find_one({"user_id": payload.user_id})
    visits = imp.get("visits", 0)
    level = 0
    if visits >= 20:
        level = 3
    elif visits >= 10:
        level = 2
    elif visits >= 3:
        level = 1
    db.impact.update_one({"user_id": payload.user_id}, {"$set": {"terra_level": level}})
    imp = db.impact.find_one({"user_id": payload.user_id})
    imp.pop("_id", None)
    return {"impact": imp}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
