from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

# Dizionario per riconoscere al volo i servizi più comuni
KNOWN_TRACKERS = {
    "google-analytics.com": "Google Analytics",
    "googletagmanager.com": "Google Tag Manager",
    "facebook.net": "Meta Pixel",
    "connect.facebook.net": "Meta Pixel",
    "js.stripe.com": "Stripe",
    "cloudflare.com": "Cloudflare CDN",
    "hotjar.com": "Hotjar",
    "intercom.io": "Intercom"
}

def analyze_website(url: str) -> dict:
    print(f"🕵️ Avvio scansione reale per: {url}")
    
    # Usiamo la versione SINCRONA di Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            # Navighiamo verso l'URL (senza await)
            page.goto(url, wait_until="networkidle", timeout=15000)
            
            # 1. ESTRAZIONE COOKIE
            cookies = context.cookies()
            
            # 2. ESTRAZIONE SCRIPT
            scripts = page.evaluate(
                "() => Array.from(document.scripts).map(s => s.src).filter(src => src !== '')"
            )
            
            # 3. ANALISI DEI RISULTATI
            detected_services = set()
            third_party_scripts = []
            
            domain_url = urlparse(url).netloc
            
            for script_url in scripts:
                script_domain = urlparse(script_url).netloc
                if domain_url not in script_domain and script_domain != "":
                    third_party_scripts.append(script_url)
                    
                    for tracker_domain, service_name in KNOWN_TRACKERS.items():
                        if tracker_domain in script_domain:
                            detected_services.add(service_name)
                            
            risk_score = min(100, 20 + (len(cookies) * 2) + (len(detected_services) * 10))

            result = {
                "url": url,
                "total_cookies": len(cookies),
                "cookies_data": [{"name": c["name"], "domain": c["domain"]} for c in cookies],
                "total_third_party_scripts": len(third_party_scripts),
                "detected_services": list(detected_services),
                "risk_score": risk_score
            }
            
            print(f"✅ Scansione completata. Score: {risk_score}/100. Trovati: {detected_services}")
            return result
            
        except Exception as e:
            print(f"❌ Errore durante la scansione di {url}: {str(e)}")
            return {"error": str(e)}
        finally:
            browser.close()