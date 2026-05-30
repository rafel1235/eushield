(function() {
    // 1. Trova lo script corrente per leggere la configurazione dal tag HTML
    const currentScript = document.currentScript || document.querySelector('script[src*="banner.js"]');
    if (!currentScript) return;

    // Estraiamo le configurazioni passate dal nostro backend
    const projectId = currentScript.getAttribute('data-project') || 'unknown';
    const lang = currentScript.getAttribute('data-lang') || 'it';
    const theme = currentScript.getAttribute('data-theme') || 'light';
    const position = currentScript.getAttribute('data-pos') || 'bottom';

    // 2. Controlla se l'utente ha già fatto una scelta in precedenza
    const storageKey = `eushield_consent_${projectId}`;
    if (localStorage.getItem(storageKey)) {
        // Se ha già risposto, non mostriamo il banner
        return; 
    }

    // 3. Dizionario delle traduzioni base
    const translations = {
        it: { text: "Questo sito utilizza cookie per migliorare la tua esperienza.", accept: "Accetta tutti", reject: "Rifiuta" },
        en: { text: "This website uses cookies to improve your experience.", accept: "Accept All", reject: "Reject" },
        fr: { text: "Ce site utilise des cookies pour améliorer votre expérience.", accept: "Tout accepter", reject: "Refuser" }
    };
    const t = translations[lang] || translations['it'];

    // 4. Iniettiamo gli stili CSS in base al tema e alla posizione scelti
    const style = document.createElement('style');
    style.innerHTML = `
        #eushield-banner {
            position: fixed;
            ${position === 'bottom' ? 'bottom: 0; left: 0; right: 0; width: 100%;' : 'bottom: 20px; left: 20px; max-width: 400px; border-radius: 8px; border: 1px solid #e5e7eb;'}
            background-color: ${theme === 'dark' ? '#1f2937' : '#ffffff'};
            color: ${theme === 'dark' ? '#f3f4f6' : '#111827'};
            padding: 16px 24px;
            box-shadow: 0 -10px 15px -3px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: ${position === 'bottom' ? 'row' : 'column'};
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            z-index: 999999;
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 14px;
            box-sizing: border-box;
        }
        .eushield-buttons { display: flex; gap: 8px; width: ${position === 'bottom' ? 'auto' : '100%'}; justify-content: flex-end; }
        .eushield-btn {
            padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; transition: opacity 0.2s;
        }
        .eushield-btn:hover { opacity: 0.8; }
        .eushield-btn-accept { background: #3b82f6; color: white; }
        .eushield-btn-reject { background: transparent; border: 1px solid ${theme === 'dark' ? '#4b5563' : '#d1d5db'}; color: inherit; }
    `;
    document.head.appendChild(style);

    // 5. Costruiamo l'HTML del banner e lo mettiamo nel body
    const banner = document.createElement('div');
    banner.id = 'eushield-banner';
    banner.innerHTML = `
        <div style="line-height: 1.5;">${t.text}</div>
        <div class="eushield-buttons">
            <button class="eushield-btn eushield-btn-reject" id="eushield-reject">${t.reject}</button>
            <button class="eushield-btn eushield-btn-accept" id="eushield-accept">${t.accept}</button>
        </div>
    `;
    document.body.appendChild(banner);

   // Funzione helper per inviare i dati al nostro backend in modo invisibile (Asincrono)
    function sendConsentLog(action, preferences) {
        // NOTA: Quando andrai online, questo sarà 'https://api.eushield.eu/api/consent'
        fetch('http://127.0.0.1:8000/api/consent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: projectId,
                action: action,
                preferences: preferences
            })
        }).catch(err => console.error("EUShield: log error", err));
    }

    // 6. Gestiamo i click sui pulsanti
    document.getElementById('eushield-accept').addEventListener('click', () => {
        localStorage.setItem(storageKey, 'accepted');
        banner.remove();
        
        // NOVITÀ: Salviamo il log nel Database di EUShield!
        sendConsentLog('accepted', { analytics: true, marketing: true, necessary: true });
        
        // Attiviamo i tracker sul sito del cliente
        window.dispatchEvent(new Event('eushield_consent_accepted'));
    });

    document.getElementById('eushield-reject').addEventListener('click', () => {
        localStorage.setItem(storageKey, 'rejected');
        banner.remove();
        
        // NOVITÀ: Salviamo il log del rifiuto
        sendConsentLog('rejected', { analytics: false, marketing: false, necessary: true });
        
        window.dispatchEvent(new Event('eushield_consent_rejected'));
    });
})();