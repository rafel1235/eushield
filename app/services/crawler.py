from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import uuid
from app.models.database import SessionLocal, Scan, ScanTracker

# 1. Dizionario dei famosi (ora con le tue categorie in italiano)
KNOWN_TRACKERS = {
    "google-analytics.com": {"name": "Google Analytics", "category": "Analytics"},
    "googletagmanager.com": {"name": "Google Tag Manager", "category": "Analytics"},
    "facebook.net": {"name": "Meta Pixel", "category": "Pubblicità"},
    "connect.facebook.net": {"name": "Meta Pixel", "category": "Pubblicità"},
    "js.stripe.com": {"name": "Stripe", "category": "Sistemi di pagamento"},
    "cloudflare.com": {"name": "Cloudflare CDN", "category": "Servizi di terze parti"},
    "hotjar.com": {"name": "Hotjar", "category": "Analytics"},
    "intercom.io": {"name": "Intercom", "category": "Chat Widget"}
}

# 2. Il nostro "Motore AI" per classificare gli script sconosciuti
def guess_tracker_category(url: str) -> str:
    url_lower = url.lower()
    if any(keyword in url_lower for keyword in ["ads", "pixel", "banner", "marketing", "sponsor"]):
        return "Pubblicità"
    if any(keyword in url_lower for keyword in ["stat", "analytic", "track", "metric"]):
        return "Analytics"
    if any(keyword in url_lower for keyword in ["pay", "checkout", "cart"]):
        return "Sistemi di pagamento"
    if any(keyword in url_lower for keyword in ["chat", "bot", "support", "helpdesk"]):
        return "Chat Widget"
    if any(keyword in url_lower for keyword in ["form", "captcha", "survey"]):
        return "Form"
    return "Servizi di terze parti" # Default se non trova nulla

def analyze_website(url: str, project_id: str) -> dict:
    print(f"🕵️ Avvio scansione intelligente per: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="load", timeout=30000)
            page.wait_for_timeout(3000) 
            
            cookies = context.cookies()
            scripts = page.evaluate("() => Array.from(document.scripts).map(s => s.src).filter(src => src !== '')")
            
            detected_trackers = []
            domain_url = urlparse(url).netloc
            
            # --- ANALISI SCRIPT ---
            for script_url in scripts:
                script_domain = urlparse(script_url).netloc
                if domain_url not in script_domain and script_domain != "":
                    is_known = False
                    # Controllo famosi
                    for tracker_domain, info in KNOWN_TRACKERS.items():
                        if tracker_domain in script_domain:
                            if not any(t['name'] == info['name'] for t in detected_trackers):
                                detected_trackers.append(info)
                            is_known = True
                            break
                    
                    # Controllo sconosciuti (Uso euristica)
                    if not is_known:
                        clean_domain = script_domain.replace("www.", "")
                        category = guess_tracker_category(script_url)
                        if not any(t['name'] == clean_domain for t in detected_trackers):
                            detected_trackers.append({
                                "name": clean_domain,
                                "category": category
                            })
                            
            # --- INSERIMENTO COOKIE NELLA LISTA ---
            for c in cookies:
                if not any(t['name'] == f"Cookie: {c['name']}" for t in detected_trackers):
                    detected_trackers.append({
                        "name": f"Cookie: {c['name']}",
                        "category": "Cookie"
                    })

            risk_score = min(100, 20 + (len(cookies) * 2) + (len(detected_trackers) * 10))

            # Salvataggio DB...
            db = SessionLocal()
            try:
                db_scan = Scan(project_id=uuid.UUID(project_id), risk_score=risk_score, total_cookies=len(cookies))
                db.add(db_scan)
                db.commit()
                db.refresh(db_scan)
                for tracker in detected_trackers:
                    db.add(ScanTracker(scan_id=db_scan.id, tracker_name=tracker["name"], category=tracker["category"]))
                db.commit()
            except Exception as db_error:
                print(f"❌ Errore DB: {db_error}")
            finally:
                db.close()

            return {
                "url": url,
                "total_cookies": len(cookies),
                "risk_score": risk_score,
                "trackers_found": detected_trackers
            }
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            browser.close()