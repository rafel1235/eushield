from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional, List, Dict, Literal
from uuid import UUID

# --- MODULO A: SCANNER ---
class ScanRequest(BaseModel):
    url: HttpUrl
    project_id: UUID

class ScanResult(BaseModel):
    task_id: str
    status: str # "pending", "processing", "completed", "failed"

# --- MODULO D: DSAR ---
class DsarCreate(BaseModel):
    project_id: UUID
    name: str
    email: EmailStr
    request_type: Literal["access", "delete", "rectify"] # Validazione automatica
    details: Optional[str] = None

class DsarResponse(BaseModel):
    id: UUID
    status: str
    message: str

# --- MODULO B: COOKIE BANNER ---
class BannerConfigRequest(BaseModel):
    project_id: UUID
    language: Literal["it", "en", "de", "fr", "es"] = "it"
    theme: Literal["light", "dark"] = "light"
    position: Literal["bottom", "modal"] = "bottom"

class BannerResponse(BaseModel):
    script_snippet: str
    instructions: str  