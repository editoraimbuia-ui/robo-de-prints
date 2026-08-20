import os
import requests
import smtplib
from datetime import datetime
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = "editoraimbuia@gmail.com"           # O Gmail oficial que envia
EMAIL_DESTINATARIO = "gazetadoparana01@hotmail.com"   # O e-mail que recebe os prints

# Senha de app de 16 caracteres gerada na conta editoraimbuia@gmail.com
SENHA_APP = "ofxi lkzn ymno mojw"

# URL para ler os dados da planilha
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

def obter_valor_chaves(dicionario, *chaves):
    dicionario_normalizado = {str(k).strip().lower(): v for k, v in dicionario.items()}
    for chave in chaves:
        chave_normalizada = chave.strip().lower()
        if chave_normalizada in dicionario_normalizado:
            return dicionario_normalizado[chave_normalizada]
    return None

def enviar_email_com_anexos(arquivos_prints, data_hoje):
    if not arquivos_prints:
        print("Nenhum print foi gerado para enviar por e-mail.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"Comprovantes de Prints - {data_hoje.strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg.set_content(f"Olá!\n\nSegue em anexo a captura de tela dos {len(arquivos_prints)} banners ativos em {data_hoje.strftime('%d/%m/%Y')}.")

    for caminho_arquivo in arquivos_prints:
        nome_arquivo = os.path.basename(caminho_arquivo)
        with open(caminho_arquivo, 'rb') as f:
            dados_arquivo = f.read()
            msg.add_attachment(dados_arquivo, maintype='image', subtype='png', filename=nome_arquivo)

    try:
        senha_limpa = SENHA_APP.replace(" ", "")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_REMETENTE, senha_limpa)
            smtp.send_message(msg)
        print(f"Sucesso! E-mail enviado com {len(arquivos_prints)} print(s) anexado(s).")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

def executar():
    hoje = datetime.now().date()
    print(f"--- Início do Processamento: {hoje} ---")

    try:
        res = requests.get(WEBAPP_URL, allow_redirects=True)
        campanhas = res.json()
        print(f"Total de registros na planilha: {len(campanhas)}")
    except Exception as e:
        print(f"Erro ao buscar planilha: {e}")
        return

    os.makedirs("prints", exist_ok=True)
    prints_gerados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for c in campanhas:
            cliente = obter_valor_chaves(c, "cliente", "Cliente") or "Cliente"
            url = obter_valor_chaves(c, "url", "URL")
            posicao = obter_valor_chaves(c, "posicao", "Posição", "Posicao") or "Posicao"
            status = obter_valor_chaves(c, "status", "Status") or ""
            
            d_inicio = converter_data(obter_valor_chaves(c, "data_inicio", "data inicio", "Data Início"))
            d_fim = converter_data(obter_valor_chaves(c, "data_fim", "data fim", "Data Fim"))

            if str(status).strip().lower() != "ativo":
                continue

            if d_inicio and d_fim and not (d_inicio <= hoje <= d_fim):
                continue

            if not url:
                continue

            print(f"Capturando: {cliente} - {posicao}")

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                nome_arquivo = f"{cliente}_{posicao}_{hoje}.png".replace(" ", "_").replace("/", "-")
                caminho_local = os.path.join("prints", nome_arquivo)

                page.screenshot(path=caminho_local, full_page=True)
                prints_gerados.append(caminho_local)

            except Exception as e:
                print(f"Erro ao capturar {cliente}: {e}")

        browser.close()

    enviar_email_com_anexos(prints_gerados, hoje)

if __name__ == "__main__":
    executar()
