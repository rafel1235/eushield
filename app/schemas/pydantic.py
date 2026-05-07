from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional, List, Dict
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
    request_type: str # "access", "delete", "rectify"
    details: Optional[str] = None

class DsarResponse(BaseModel):
    id: UUID
    status: str
    message: str