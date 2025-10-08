import requests
import json
import os
import time
from datetime import datetime, timedelta

# Configurazione base
HEADERS = {
    "User-Agent": "deliberation-ontology-dev-1.0.0"
}

# Creare directory per salvare i dati
os.makedirs("ep_debates", exist_ok=True)

def get_recent_plenary_dates(num_dates=5):
    """Ottiene le date recenti delle sessioni plenarie."""
    # Date fisse recenti di sessioni plenarie
    known_plenary_dates = [
        "2025-03-10",
        "2025-03-11",
        "2025-03-12",
        "2025-02-28",
        "2025-02-12",
    ]
    
    return known_plenary_dates[:num_dates]

def download_verbatim_reports(dates):
    """Scarica i verbatim reports direttamente dal sito web del Parlamento Europeo."""
    term_num = "10"  # 10° termine parlamentare
    
    for date in dates:
        year, month, day = date.split("-")
        
        # Costruisci l'URL per il documento verbatim HTML sul sito ufficiale
        verbatim_url = f"https://www.europarl.europa.eu/doceo/document/CRE-{term_num}-{year}-{month}-{day}_EN.html"
        print(f"\nTentativo di accesso al verbatim report: {verbatim_url}")
        
        try:
            response = requests.get(verbatim_url, headers=HEADERS)
            
            if response.status_code == 200:
                print(f"✓ Documento verbatim trovato per la data {date}")
                
                # Salva l'URL per riferimento
                with open(f"ep_debates/verbatim_url_{date}.txt", "w", encoding="utf-8") as f:
                    f.write(verbatim_url)
                
                # Salva il documento HTML
                with open(f"ep_debates/verbatim_{date}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                    
                print(f"HTML salvato: ep_debates/verbatim_{date}.html")
                
                # Crea un link per aprire direttamente nel browser
                print(f"Apri il documento nel browser: {verbatim_url}")
                
            else:
                print(f"✗ Nessun documento verbatim trovato per la data {date} (Status: {response.status_code})")
        
        except Exception as e:
            print(f"Errore durante il recupero del documento per la data {date}: {str(e)}")
        
        # Pausa tra le richieste
        time.sleep(1)

# Esecuzione
if __name__ == "__main__":
    print("Ottenimento date recenti delle sessioni plenarie...")
    plenary_dates = get_recent_plenary_dates(3)
    print(f"Date delle sessioni plenarie da processare: {plenary_dates}")
    
    download_verbatim_reports(plenary_dates)