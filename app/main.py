import hashlib
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uuid
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.schemas.pydantic import (
    ScanRequest, ScanResult, 
    DsarCreate, DsarResponse,
    BannerConfigRequest, BannerResponse,
    ConsentLogCreate
)
from app.models.database import SessionLocal, ConsentLog
from app.services.crawler import analyze_website

app = FastAPI(
    title="EUShield API",
    description="API per la generazione di compliance kit GDPR",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory="public"), name="public")

# ==========================================
# ENDPOINT MODULO A: SCANNER (DIRETTO PER LA DASHBOARD)
# ==========================================
@app.post("/api/scan", tags=["Scanner"])
def start_scan(request: ScanRequest):  # <--- HO TOLTO 'async' QUI!
    """
    Riceve un URL, avvia il crawler e restituisce i risultati DIRETTAMENTE alla UI.
    """
    scan_results = analyze_website(str(request.url), str(request.project_id))
    return scan_results

# ==========================================
# ENDPOINT MODULO D: DSAR
# ==========================================
@app.post("/api/dsar", response_model=DsarResponse, tags=["DSAR"])
async def submit_dsar_request(dsar: DsarCreate):
    request_id = uuid.uuid4()
    return {
        "id": request_id,
        "status": "pending",
        "message": "Richiesta ricevuta. Il titolare del trattamento ti contatterà entro 30 giorni."
    }

# ==========================================
# ENDPOINT MODULO B: COOKIE BANNER
# ==========================================
@app.post("/api/banner/generate", response_model=BannerResponse, tags=["Banner"])
async def generate_banner(config: BannerConfigRequest):
    cdn_url = "https://cdn.eushield.eu/banner.js"
    snippet = f"""<script src="{cdn_url}" data-project="{config.project_id}" data-lang="{config.language}" data-theme="{config.theme}" data-pos="{config.position}" defer></script>"""
    return {"script_snippet": snippet, "instructions": "Copia e incolla."}

# ==========================================
# ENDPOINT MODULO B: RICEZIONE LOG CONSENSO
# ==========================================
@app.post("/api/consent", tags=["Banner"])
async def log_consent(consent: ConsentLogCreate, request: Request):
    raw_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(raw_ip.encode('utf-8')).hexdigest()
    db = SessionLocal()
    try:
        new_log = ConsentLog(
            project_id=consent.project_id,
            ip_hash=ip_hash,
            action=consent.action,
            preferences=consent.preferences
        )
        db.add(new_log)
        db.commit()
        print(f"🔒 Log Consenso salvato! Progetto: {consent.project_id} | Azione: {consent.action}")
        return {"status": "success", "message": "Consent logged securely."}
    except Exception as e:
        print(f"❌ Errore nel salvataggio del log: {e}")
        return {"error": "Failed to log consent"}
    finally:
        db.close()