import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

API_URL = "https://script.google.com/macros/s/AKfycbxBXeDIie_Ler7HRrfQKMp1S-nr8NJNw-P8L8aCQr7Axtomizye0xpvSKu9EsMyrp2mkw/exec"

def executar_prints():
    # Cria a pasta obrigatoriamente no início
    os.makedirs("prints", exist_ok=True)
    
    try:
        response = requests.get(API_URL)
        campanhas = response.json()
        print(f"Dados recebidos da planilha: {campanhas}")
    except Exception as e:
        print(f"Erro ao buscar dados da API: {e}")
        campanhas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        capturou_algum = False
        for item in campanhas:
            status = str(item.get("status", "")).strip().upper()
            url = str(item.get("url", "")).strip()
            cliente = str(item.get("cliente", "Cliente")).strip()
            
            if status == "ATIVO" and url:
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                    
                print(f"Tirando print de: {cliente} ({url})")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    data_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
                    nome_arquivo = f"prints/{cliente}_{data_str}.png"
                    page.screenshot(path=nome_arquivo, full_page=True)
                    print(f"Sucesso: {nome_arquivo}")
                    capturou_algum = True
                except Exception as e:
                    print(f"Erro em {url}: {e}")

        # Garante um arquivo dummy caso não haja campanhas ativas
        if not capturou_algum:
            with open("prints/aviso.txt", "w") as f:
                f.write("Nenhuma campanha ATIVA com URL valida foi encontrada na planilha.")

        browser.close()

if __name__ == "__main__":
    executar_prints()
