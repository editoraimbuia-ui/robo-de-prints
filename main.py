import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# URL da sua API no Google Apps Script
API_URL = "https://script.google.com/macros/s/AKfycbxBXeDIie_Ler7HRrfQKMp1S-nr8NJNw-P8L8aCQr7Axtomizye0xpvSKu9EsMyrp2mkw/exec"

def executar_prints():
    # 1. Busca as campanhas cadastradas na planilha
    response = requests.get(API_URL)
    campanhas = response.json()
    
    # Cria a pasta para salvar os prints temporariamente
    os.makedirs("prints", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        for item in campanhas:
            # Roda apenas campanhas marcadas como ATIVO
            if str(item.get("status")).strip().upper() == "ATIVO":
                cliente = item.get("cliente", "Cliente")
                url = item.get("url")
                
                if url:
                    print(f"Acessando: {cliente} -> {url}")
                    try:
                        page.goto(url, wait_until="networkidle", timeout=30000)
                        
                        data_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
                        nome_arquivo = f"prints/{cliente}_{data_str}.png"
                        
                        page.screenshot(path=nome_arquivo, full_page=True)
                        print(f"Print salvo: {nome_arquivo}")
                    except Exception as e:
                        print(f"Erro ao capturar {url}: {e}")
                        
        browser.close()

if __name__ == "__main__":
    executar_prints()
