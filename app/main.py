from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import sys
import asyncio

# --- FIX PER WINDOWS + PLAYWRIGHT ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ------------------------------------

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid

# Importiamo gli schemi che abbiamo creato
from app.schemas.pydantic import ScanRequest, ScanResult, DsarCreate, DsarResponse

app = FastAPI(
    title="EUShield API",
    description="API per la generazione di compliance kit GDPR",
    version="0.1.0"
)

# Configurazione CORS (Per far parlare Next.js con FastAPI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://eushield.eu"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FUNZIONE FINTA PER IL BACKGROUND TASK ---
# (In futuro, qui chiameremo Playwright o lo manderemo a Celery/Redis)
# Importa la funzione che abbiamo appena creato!
from app.services.crawler import analyze_website

# ... (tieni il resto del file com'è, fino alla funzione in background) ...

# AGGIORNA QUESTA FUNZIONE
# NOTA: non c'è più "async def", solo "def"
def run_playwright_scan(task_id: str, url: str):
    print(f"[TASK {task_id}] Inizio elaborazione in background...")
    
    # Eseguiamo il crawler (non c'è più "await")
    scan_results = analyze_website(url)
    
    print(f"\n--- RISULTATI SCAN {task_id} ---")
    import json
    print(json.dumps(scan_results, indent=2))
    print("----------------------------------\n")

# ... (il resto degli endpoint rimane identico) ...

# ==========================================
# ENDPOINT MODULO A: SCANNER
# ==========================================
@app.post("/api/scan", response_model=ScanResult, tags=["Scanner"])
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Riceve un URL, avvia il crawler in background e restituisce un task_id.
    Il frontend farà polling o userà WebSocket per sapere quando ha finito.
    """
    task_id = str(uuid.uuid4())
    
    # Passiamo il lavoro pesante in background
    background_tasks.add_task(run_playwright_scan, task_id, str(request.url))
    
    return {"task_id": task_id, "status": "processing"}

# ==========================================
# ENDPOINT MODULO D: DSAR
# ==========================================
@app.post("/api/dsar", response_model=DsarResponse, tags=["DSAR"])
async def submit_dsar_request(dsar: DsarCreate):
    """
    Endpoint pubblico (domain.com/privacy-request) per gli utenti finali 
    che vogliono esercitare i propri diritti GDPR.
    """
    # Qui inseriremo la logica di salvataggio su PostgreSQL
    request_id = uuid.uuid4()
    
    # TODO: Inviare email automatica al proprietario del sito (Titolare del trattamento)
    
    return {
        "id": request_id,
        "status": "pending",
        "message": "Richiesta ricevuta. Il titolare del trattamento ti contatterà entro 30 giorni."
    }