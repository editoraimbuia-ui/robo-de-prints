import os
import requests
import smtplib
from datetime import datetime
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = "editoraimbuia@gmail.com"
EMAIL_DESTINATARIO = "gazetadoparana01@hotmail.com"
SENHA_APP = "ofxi lkzn ymno mojw"

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
    # Se não houver prints gerados, o robô encerra sem mandar e-mail
    if not arquivos_prints:
        print("Nenhuma campanha ativa hoje. E-mail não enviado.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"Comprovantes de Prints - {data_hoje.strftime('%d/%m/%Y')}"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg.set_content(
        f"Olá!\n\nSegue em anexo o relatório diário das 08:00 AM contendo as capturas de tela "
        f"dos {len(arquivos_prints)} banners ativos em {data_hoje.strftime('%d/%m/%Y')}."
    )

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
        print(f"Sucesso! 1 e-mail unificado enviado contendo {len(arquivos_prints)} print(s).")
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
        # Resolução de tela padrão desktop
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for c in campanhas:
            cliente = obter_valor_chaves(c, "cliente", "Cliente") or "Cliente"
            url = obter_valor_chaves(c, "url", "URL")
            posicao = obter_valor_chaves(c, "posicao", "Posição", "Posicao", "Espaco", "Espaço") or "1"
            status = obter_valor_chaves(c, "status", "Status") or ""
            
            d_inicio = converter_data(obter_valor_chaves(c, "data_inicio", "data inicio", "Data Início"))
            d_fim = converter_data(obter_valor_chaves(c, "data_fim", "data fim", "Data Fim"))

            # Validação: ignora se não estiver "Ativo"
            if str(status).strip().lower() != "ativo":
                continue

            # Validação: ignora se estiver fora da data de vigência
            if d_inicio and d_fim and not (d_inicio <= hoje <= d_fim):
                continue

            if not url:
                continue

            print(f"Processando: {cliente} (Espaço {posicao})")

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Ajuste automático de scroll conforme a numeração do Espaço (1 a 7)
                posicao_str = str(posicao).strip()
                if posicao_str in ["3", "4"]:
                    page.evaluate("window.scrollBy(0, 450);")
                    page.wait_for_timeout(1000)
                elif posicao_str in ["5", "6", "7"]:
                    page.evaluate("window.scrollBy(0, 1100);")
                    page.wait_for_timeout(1000)

                nome_arquivo = f"{cliente}_Espaco_{posicao_str}_{hoje}.png".replace(" ", "_").replace("/", "-")
                caminho_local = os.path.join("prints", nome_arquivo)

                # full_page=False para capturar a área enquadrada do viewport
                page.screenshot(path=caminho_local, full_page=False)
                prints_gerados.append(caminho_local)

            except Exception as e:
                print(f"Erro ao capturar {cliente}: {e}")

        browser.close()

    # Dispara apenas 1 e-mail com os anexos do dia
    enviar_email_com_anexos(prints_gerados, hoje)

if __name__ == "__main__":
    executar()
