import hashlib
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uuid
import sys
import asyncio
from datetime import datetime
from app.models.database import SessionLocal, ConsentLog, Policy # <--- Aggiunto Policy
from app.schemas.pydantic import (
    ScanRequest, ScanResult, 
    DsarCreate, DsarResponse,
    BannerConfigRequest, BannerResponse,
    ConsentLogCreate, PolicyRequest, PolicyResponse # <--- Aggiunti questi due
)

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


# ==========================================
# ENDPOINT MODULO C: PRIVACY POLICY GENERATOR
# ==========================================
@app.post("/api/policy/generate", response_model=PolicyResponse, tags=["Policy"])
def generate_policy(request: PolicyRequest):
    # Generazione Testo Legale Dinamico
    date_str = datetime.now().strftime('%d/%m/%Y')
    
    html = f"""
    <div style="font-family: sans-serif; line-height: 1.6; color: #333;">
        <h1 style="color: #2563eb;">Informativa sulla Privacy</h1>
        <p><em>Ultimo aggiornamento: {date_str}</em></p>
        
        <h2>1. Titolare del Trattamento</h2>
        <p>Il Titolare tratta i dati personali degli utenti adottando le opportune misure di sicurezza volte ad impedire l'accesso, la divulgazione, la modifica o la distruzione non autorizzate dei Dati Personali.</p>
        
        <h2>2. Dati Raccolti e Finalità</h2>
        <p>Questo sito raccoglie i seguenti dati per le finalità specificate:</p>
        <ul>
    """
    
    if request.has_ecommerce:
        html += "<li><strong>E-commerce:</strong> Dati di fatturazione e spedizione per evadere gli ordini.</li>"
    if request.collects_email:
        html += "<li><strong>Contatti:</strong> Indirizzo email ed eventuali dati anagrafici inviati tramite moduli di contatto.</li>"
    if request.receives_payments:
        html += "<li><strong>Pagamenti:</strong> Gestiti in modo sicuro tramite provider esterni. Il sito non salva i numeri delle carte di credito.</li>"
    if request.uses_analytics:
        html += "<li><strong>Statistiche:</strong> Dati di navigazione e utilizzo, raccolti in forma aggregata (es. tramite Google Analytics) per migliorare il servizio.</li>"
    if request.uses_newsletter:
        html += "<li><strong>Marketing:</strong> Previo consenso, l'email può essere utilizzata per l'invio di materiale promozionale.</li>"
        
    html += """
        </ul>
        <h2>3. Diritti dell'Utente (GDPR)</h2>
        <p>In qualunque momento l'utente può richiedere l'accesso, la rettifica o la cancellazione dei propri dati tramite l'apposito portale Privacy.</p>
    </div>
    """
    
 # Salvataggio nel Database
    db = SessionLocal()
    try:
        new_policy = Policy(
            project_id=request.project_id,
            # ✨ IL SEGRETO È QUI: Aggiungiamo mode='json' per convertire l'UUID in semplice testo!
            answers_json=request.model_dump(mode='json'), 
            html_content=html
        )
        db.add(new_policy)
        db.commit()
        db.refresh(new_policy)
        return {"policy_id": new_policy.id, "html_content": html, "message": "Policy generata con successo!"}
    except Exception as e:
        print(f"❌ Errore Database Policy: {e}")
        # ✨ Solleviamo un vero errore HTTP così il frontend lo capisce, invece di confondere FastAPI
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()       