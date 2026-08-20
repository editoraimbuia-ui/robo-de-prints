import os
import requests
import base64
from datetime import datetime
from playwright.sync_api import sync_playwright

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzioUR51hOg2vI5GRu7PNNRae_x4YTI1Y_eSYUj0P3D_7A3J7xSkfXsAnO-9NLQN4w/exec"

def converter_data(data_str):
    try:
        if isinstance(data_str, str):
            return datetime.strptime(data_str.split("T")[0], "%Y-%m-%d").date()
    except:
        try:
            return datetime.strptime(str(data_str).strip(), "%d/%m/%Y").date()
        except:
            return None
    return None

def enviar_para_google_drive(caminho_arquivo, nome_arquivo):
    try:
        with open(caminho_arquivo, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "fileName": nome_arquivo,
            "mimeType": "image/png",
            "base64": encoded_string
        }

        res = requests.post(WEBAPP_URL, json=payload)
        print(f"Envio ao Drive ({nome_arquivo}): {res.text}")
    except Exception as e:
        print(f"Erro ao enviar {nome_arquivo} para o Drive: {e}")

def executar():
    hoje = datetime.now().date()
    print(f"--- Início do Processamento: {hoje} ---")

    try:
        res = requests.get(WEBAPP_URL)
        campanhas = res.json()
    except Exception as e:
        print(f"Erro ao buscar dados do Apps Script: {e}")
        return

    os.makedirs("prints", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for c in campanhas:
            cliente = c.get("cliente")
            url = c.get("url")
            posicao = c.get("posicao")
            status = c.get("status")
            d_inicio = converter_data(c.get("data_inicio"))
            d_fim = converter_data(c.get("data_fim"))

            if status != "Ativo":
                continue

            if d_inicio and d_fim:
                if not (d_inicio <= hoje <= d_fim):
                    continue

            print(f"Capturando print de: {cliente} | {url}")

            try:
                # Aguarda até 60s (60000ms) carregando a estrutura da página
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                # Aguarda +3s para dar tempo dos scripts e banners renderizarem
                page.wait_for_timeout(3000)

                nome_arquivo = f"{cliente}_{posicao}_{hoje}.png".replace(" ", "_").replace("/", "-")
                caminho_local = os.path.join("prints", nome_arquivo)

                page.screenshot(path=caminho_local, full_page=True)
                print(f"Print gerado localmente: {nome_arquivo}")

                enviar_para_google_drive(caminho_local, nome_arquivo)

            except Exception as e:
                print(f"Erro/Timeout ao capturar print de {cliente}: {e}")
                continue

        browser.close()

if __name__ == "__main__":
    executar()
