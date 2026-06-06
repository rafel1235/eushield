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
from app.models.database import User, Project
from app.schemas.pydantic import AuthRequest, ProjectCreate

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
            project_id=str(consent.project_id),
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
    
    # ... (codice precedente dell'endpoint) ...
    
    if request.uses_newsletter:
        html += "<li><strong>Marketing:</strong> Previo consenso, l'email può essere utilizzata per l'invio di materiale promozionale.</li>"
        
    html += "</ul>"

    # ✨ IL NUOVO MOTORE DINAMICO: Scrive la policy in base a ciò che ha trovato!
    html += "<h2>3. Servizi di Terze Parti e Tracciamento</h2>"
    html += "<p>Durante la scansione automatizzata del sito, sono stati rilevati i seguenti servizi che potrebbero trattare dati personali:</p><ul>"
    
    if request.detected_trackers:
        for t in request.detected_trackers:
            name = t.get('name', 'Servizio Sconosciuto')
            cat = t.get('category', 'Non classificato')
            
            if cat == 'Pubblicità':
                html += f"<li><strong>{name} (Profilazione/Marketing):</strong> Raccoglie dati sul comportamento dell'utente per fornire annunci personalizzati. Il trasferimento dati potrebbe avvenire fuori dallo Spazio Economico Europeo (SEE).</li>"
            elif cat == 'Analytics':
                html += f"<li><strong>{name} (Statistica):</strong> Utilizzato per analizzare il traffico del sito web. I dati sono raccolti in forma aggregata.</li>"
            elif cat == 'Sistemi di pagamento':
                html += f"<li><strong>{name} (Transazioni):</strong> Gestisce in modo sicuro le transazioni finanziarie senza che il Titolare abbia accesso ai dati completi della carta.</li>"
            elif cat == 'Cookie':
                html += f"<li><strong>{name} (Tecnico/Tracciamento):</strong> Marcatore memorizzato sul browser dell'utente per mantenere la sessione o le preferenze.</li>"
            else:
                html += f"<li><strong>{name} ({cat}):</strong> Servizio tecnico di terze parti integrato nella piattaforma.</li>"
    else:
        html += "<li>Nessun servizio di tracciamento di terze parti invasivo è stato rilevato durante l'ultima scansione.</li>"

    html += """
        </ul>
        <h2>4. Diritti dell'Utente (GDPR)</h2>
        <p>In qualunque momento l'utente può richiedere l'accesso, la rettifica o la cancellazione dei propri dati tramite l'apposito portale Privacy.</p>
    </div>
    """
# ... (lascia il salvataggio nel database com'è) ...
    
 # Salvataggio nel Database
    db = SessionLocal()
    try:
        new_policy = Policy(
            project_id=str(request.project_id),
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


# ==========================================
# ENDPOINT MODULO ONBOARDING (ACCOUNT E PROGETTI)
# ==========================================
@app.post("/api/auth/magic-link", tags=["Auth"])
def send_magic_link(req: AuthRequest):
    db = SessionLocal()
    try:
        # Cerca l'utente. Se non esiste, lo registra nuovo di zecca!
        user = db.query(User).filter(User.email == req.email).first()
        if not user:
            user = User(email=req.email)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # SIMULAZIONE MAGIC LINK
        print(f"📧 [SIMULAZIONE] Inviato Magic Link a {req.email}")
        return {"message": "Accesso consentito!", "user_id": user.id}
    finally:
        db.close()

@app.post("/api/projects", tags=["Projects"])
def create_project(req: ProjectCreate):
    db = SessionLocal()
    try:
        new_project = Project(
            user_id=str(req.user_id),
            domain_name=req.domain_name
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        print(f"🌍 Nuovo progetto creato: {new_project.domain_name}")
        return {"project_id": new_project.id, "domain_name": new_project.domain_name}
    finally:
        db.close()        