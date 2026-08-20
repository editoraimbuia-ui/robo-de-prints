import os
import requests
import base64
from datetime import datetime
from playwright.sync_api import sync_playwright

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbziOURSlbOgz2vISG8u7FfWMRwe_X4YCICY_e3YQjGF3D_t7AJ7zsWfxSeANOr3NL0N4w/exec"

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

        # allow_redirects=True garante que a requisição siga os redirecionamentos do Google
        res = requests.post(WEBAPP_URL, json=payload, allow_redirects=True)
        print(f"Resposta do Google Drive ({nome_arquivo}): {res.text}")
    except Exception as e:
        print(f"Erro ao enviar {nome_arquivo} para o Drive: {e}")

def obter_valor_chaves(dicionario, *chaves):
    """Busca o valor no dicionário ignorando maiúsculas e minúsculas"""
    dicionario_normalizado = {str(k).strip().lower(): v for k, v in dicionario.items()}
    for chave in chaves:
        chave_normalizada = chave.strip().lower()
        if chave_normalizada in dicionario_normalizado:
            return dicionario_normalizado[chave_normalizada]
    return None

def executar():
    hoje = datetime.now().date()
    print(f"--- Início do Processamento: {hoje} ---")

    try:
        res = requests.get(WEBAPP_URL, allow_redirects=True)
        campanhas = res.json()
        print(f"Total de registros recebidos do Apps Script: {len(campanhas)}")
    except Exception as e:
        print(f"Erro ao buscar dados do Apps Script: {e}")
        return

    os.makedirs("prints", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for c in campanhas:
            cliente = obter_valor_chaves(c, "cliente", "Cliente") or "Cliente_Desconhecido"
            url = obter_valor_chaves(c, "url", "Url", "URL")
            posicao = obter_valor_chaves(c, "posicao", "Posição", "Posicao") or "Posicao"
            status = obter_valor_chaves(c, "status", "Status") or ""
            
            d_inicio = converter_data(obter_valor_chaves(c, "data_inicio", "data inicio", "Data Início"))
            d_fim = converter_data(obter_valor_chaves(c, "data_fim", "data fim", "Data Fim"))

            print(f"\n--- Analisando: {cliente} ---")
            print(f"Status: '{status}' | Inicio: {d_inicio} | Fim: {d_fim} | Hoje: {hoje}")

            if str(status).strip().lower() != "ativo":
                print(f"-> Ignorado: Status não é 'Ativo'")
                continue

            if d_inicio and d_fim:
                if not (d_inicio <= hoje <= d_fim):
                    print(f"-> Ignorado: Data fora do período ({d_inicio} até {d_fim})")
                    continue

            if not url:
                print(f"-> Ignorado: URL vazia")
                continue

            print(f"-> EXECUTANDO CAPTURA: {cliente} | {url}")

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                nome_arquivo = f"{cliente}_{posicao}_{hoje}.png".replace(" ", "_").replace("/", "-")
                caminho_local = os.path.join("prints", nome_arquivo)

                page.screenshot(path=caminho_local, full_page=True)
                print(f"Print gerado localmente: {nome_arquivo}")

                enviar_para_google_drive(caminho_local, nome_arquivo)

            except Exception as e:
                print(f"Erro ao capturar print de {cliente}: {e}")
                continue

        browser.close()

if __name__ == "__main__":
    executar()
