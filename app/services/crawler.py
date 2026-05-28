from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import uuid

# Importiamo il database e i modelli che abbiamo creato
from app.models.database import SessionLocal, Scan, ScanTracker

# 1. UPGRADE: Ora mappiamo anche la "Categoria" del tracker per le tue statistiche!
KNOWN_TRACKERS = {
    "google-analytics.com": {"name": "Google Analytics", "category": "Analytics"},
    "googletagmanager.com": {"name": "Google Tag Manager", "category": "Analytics"},
    "facebook.net": {"name": "Meta Pixel", "category": "Marketing"},
    "connect.facebook.net": {"name": "Meta Pixel", "category": "Marketing"},
    "js.stripe.com": {"name": "Stripe", "category": "Necessary"},
    "cloudflare.com": {"name": "Cloudflare CDN", "category": "Necessary"},
    "hotjar.com": {"name": "Hotjar", "category": "Analytics"},
    "intercom.io": {"name": "Intercom", "category": "Marketing"}
}

# 2. UPGRADE: Ora la funzione accetta anche il project_id
def analyze_website(url: str, project_id: str) -> dict:
    print(f"🕵️ Avvio scansione reale per: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            # 1. Cambiamo "networkidle" in "load" e aumentiamo a 30 secondi
            page.goto(url, wait_until="load", timeout=30000)
            
            # 2. Forziamo una pausa di 3 secondi per far caricare i tracker più lenti
            page.wait_for_timeout(3000) 
            
            cookies = context.cookies()

            scripts = page.evaluate(
                "() => Array.from(document.scripts).map(s => s.src).filter(src => src !== '')"
            )
            
            detected_trackers = [] # Lista di dizionari con i dettagli dei tracker
            domain_url = urlparse(url).netloc
            
            for script_url in scripts:
                script_domain = urlparse(script_url).netloc
                if domain_url not in script_domain and script_domain != "":
                    for tracker_domain, info in KNOWN_TRACKERS.items():
                        if tracker_domain in script_domain:
                            # Evitiamo duplicati se ci sono più script dello stesso servizio
                            if not any(t['name'] == info['name'] for t in detected_trackers):
                                detected_trackers.append(info)
                            
            risk_score = min(100, 20 + (len(cookies) * 2) + (len(detected_trackers) * 10))

            # ==========================================
            # 3. SALVATAGGIO NEL DATABASE POSTGRESQL/SQLITE
            # ==========================================
            
            # ==========================================
            # 3. SALVATAGGIO NEL DATABASE POSTGRESQL/SQLITE
            # ==========================================
            db = SessionLocal() # Apriamo la connessione
            try:
                # A. Salviamo la scansione generale
                db_scan = Scan(
                    project_id=uuid.UUID(project_id),
                    risk_score=risk_score,
                    total_cookies=len(cookies)
                )
                db.add(db_scan)
                db.commit()
                db.refresh(db_scan)

                # B. Salviamo i tracker trovati per le tue "Classifiche"
                for tracker in detected_trackers:
                    db_tracker = ScanTracker(
                        scan_id=db_scan.id,
                        tracker_name=tracker["name"],
                        category=tracker["category"]
                    )
                    db.add(db_tracker)
                db.commit()
                print("💾 Dati salvati con successo nel Database!")
                
            except Exception as db_error:
                print(f"❌ Errore nel salvataggio sul DB: {db_error}")
            finally:
                db.close() # Chiudiamo sempre la connessione!
            # ==========================================

            # Il return finale con l'elenco completo dei cookie ripristinato
            return {
                "url": url,
                "total_cookies": len(cookies),
                "risk_score": risk_score,
                "trackers_found": detected_trackers,
                "cookies_data": [{"name": c["name"], "domain": c["domain"]} for c in cookies]
            }
            
        except Exception as e:
            print(f"❌ Errore durante la scansione: {str(e)}")
            return {"error": str(e)}
            
        finally:
            browser.close()