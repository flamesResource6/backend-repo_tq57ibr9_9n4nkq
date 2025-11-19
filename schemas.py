"""
Terra Tranquil Database Schemas

Each Pydantic model represents a MongoDB collection.
Collection name is the lowercase class name.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl

# User used only to associate impact/visits. No auth in Phase 1
class User(BaseModel):
    username: str = Field(..., description="Public username")
    avatar_url: Optional[HttpUrl] = Field(None, description="Avatar image URL")

class Business(BaseModel):
    name: str
    category: str
    location: str
    website: Optional[str] = None
    description: Optional[str] = None
    eco_checks: List[bool] = Field(default_factory=list, description="5-item checklist booleans")
    logo_url: Optional[str] = None
    eco_score: int = Field(ge=0, le=100, default=80)
    hero_image: Optional[str] = None

class Visit(BaseModel):
    user_id: str
    business_id: str
    business_name: str
    category: str
    location: str
    eco_points: int = 10

class Impact(BaseModel):
    user_id: str
    username: str
    visits: int = 0
    eco_points: int = 0
    community_impact: int = 0
    terra_level: int = 0
"""
Note: The Flames database viewer reads these schemas via GET /schema.
"""
