from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import sys
import asyncio
from fastapi.staticfiles import StaticFiles

# --- FIX PER WINDOWS + PLAYWRIGHT ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ------------------------------------

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid

# Importiamo gli schemi che abbiamo creato
from app.schemas.pydantic import (
    ScanRequest, ScanResult, 
    DsarCreate, DsarResponse,
    BannerConfigRequest, BannerResponse # <-- Aggiunti questi due
)

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
    # Servi i file statici (il tuo banner.js e index.html per i test)
)

# Servi i file statici (il tuo banner.js e index.html per i test)
app.mount("/public", StaticFiles(directory="public"), name="public")

# --- FUNZIONE FINTA PER IL BACKGROUND TASK ---
# (In futuro, qui chiameremo Playwright o lo manderemo a Celery/Redis)
# Importa la funzione che abbiamo appena creato!
from app.services.crawler import analyze_website

# ... (tieni il resto del file com'è, fino alla funzione in background) ...

# Aggiungi 'project_id' ai parametri
def run_playwright_scan(task_id: str, url: str, project_id: str):
    print(f"[TASK {task_id}] Inizio elaborazione in background...")
    
    # Passiamo sia l'URL che il project_id
    scan_results = analyze_website(url, project_id)
    
    print(f"\n--- RISULTATI SCAN {task_id} ---")
    import json
    print(json.dumps(scan_results, indent=2))
    print("----------------------------------\n")

# ... (il resto degli endpoint rimane identico) ...

# ==========================================
# ENDPOINT MODULO A: SCANNER
# ==========================================
@app.post("/api/scan", response_model=ScanResult, tags=["Scanner"])
# Aggiungi str(request.project_id) alla fine
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Riceve un URL, avvia il crawler in background e restituisce un task_id.
    Il frontend farà polling o userà WebSocket per sapere quando ha finito.
    """
    task_id = str(uuid.uuid4())
    
    # Passiamo il lavoro pesante in background
    background_tasks.add_task(run_playwright_scan, task_id, str(request.url), str(request.project_id))
    
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

# ==========================================
# ENDPOINT MODULO B: COOKIE BANNER
# ==========================================
@app.post("/api/banner/generate", response_model=BannerResponse, tags=["Banner"])
async def generate_banner(config: BannerConfigRequest):
    """
    Riceve le preferenze di stile e lingua dell'utente e genera 
    lo script HTML univoco da incorporare nel sito web.
    """
    
    # In futuro il dominio sarà il tuo vero bucket S3 o Cloudflare CDN
    cdn_url = "https://cdn.eushield.eu/banner.js"
    
    # Generiamo lo snippet. Usiamo i "data-attributes" per passare la configurazione 
    # dal sito del cliente al nostro file javascript quando verrà caricato.
    snippet = f"""<script 
    src="{cdn_url}" 
    data-project="{config.project_id}"
    data-lang="{config.language}"
    data-theme="{config.theme}"
    data-pos="{config.position}"
    defer>
</script>
"""

    return {
        "script_snippet": snippet,
        "instructions": "Copia e incolla questo codice tra i tag <head> e </head> di tutte le pagine del tuo sito web."
    }