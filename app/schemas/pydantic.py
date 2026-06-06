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

# Aggiungi 'Any' alle importazioni in alto se non c'è:
# from typing import Optional, List, Dict, Literal, Any

# ... (codice esistente) ...

class ConsentLogCreate(BaseModel):
    project_id: UUID
    action: Literal["accepted", "rejected", "customized"]
    preferences: Dict[str, bool] # es. {"marketing": true, "analytics": false}    


# ---> INCOLLA IN FONDO AL FILE <---
class PolicyRequest(BaseModel):
    project_id: UUID
    has_ecommerce: bool
    collects_email: bool
    receives_payments: bool
    uses_analytics: bool
    uses_newsletter: bool
    # ✨ LA NOVITÀ: Il generatore ora riceve i tracker scansionati!
    detected_trackers: List[Dict[str, str]] = []

class PolicyResponse(BaseModel):
    policy_id: UUID
    html_content: str
    message: str    


# ---> INCOLLA IN FONDO AL FILE <---
class AuthRequest(BaseModel):
    email: EmailStr

class ProjectCreate(BaseModel):
    user_id: UUID
    domain_name: str    