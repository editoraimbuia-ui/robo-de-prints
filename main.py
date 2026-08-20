import os
import requests
import smtplib
from datetime import datetime
from email.message import EmailMessage
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

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

def adicionar_carimbo_url_data(caminho_imagem, url, data_hora_str, cliente, espaco):
    img = Image.open(caminho_imagem)
    largura, altura = img.size
    
    altura_carimbo = 50
    nova_img = Image.new("RGB", (largura, altura + altura_carimbo), (240, 242, 245))
    nova_img.paste(img, (0, altura_carimbo))
    
    draw = ImageDraw.Draw(nova_img)
    texto = f"  URL: {url}   |   DATA/HORA: {data_hora_str}   |   CLIENTE: {cliente} (Espaço {espaco})"
    
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        
    draw.text((15, 15), texto, fill=(30, 41, 59), font=font)
    nova_img.save(caminho_imagem)

def enviar_email_com_anexos(arquivos_prints, data_hoje):
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
        print(f"Sucesso! E-mail enviado com {len(arquivos_prints)} print(s).")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

def executar():
    hoje = datetime.now().date()
    print(f"--- Início do Processamento: {hoje} ---")

    try:
        res = requests.get(WEBAPP_URL, allow_redirects=True)
        campanhas = res.json()
    except Exception as e:
        print(f"Erro ao buscar gerenciador: {e}")
        return

    os.makedirs("prints", exist_ok=True)
    prints_gerados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for c in campanhas:
            cliente = obter_valor_chaves(c, "cliente", "Cliente") or "Cliente"
            url = obter_valor_chaves(c, "url", "URL")
            posicao = str(obter_valor_chaves(c, "posicao", "Posição", "Posicao", "Espaco", "Espaço") or "1").strip().lower()
            status = obter_valor_chaves(c, "status", "Status") or ""
            
            d_inicio = converter_data(obter_valor_chaves(c, "data_inicio", "data inicio", "Data Início"))
            d_fim = converter_data(obter_valor_chaves(c, "data_fim", "data fim", "Data Fim"))

            if str(status).strip().lower() != "ativo":
                continue

            if d_inicio and d_fim and not (d_inicio <= hoje <= d_fim):
                continue

            if not url:
                continue

            print(f"Processando: {cliente} (Espaço {posicao})")

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # Scroll exato para cada espaço
                if "1" in posicao or "topo" in posicao:
                    page.evaluate("window.scrollTo(0, 0);")
                elif "2" in posicao or "principal" in posicao:
                    page.evaluate("window.scrollTo(0, 300);")
                elif "3" in posicao or "meio" in posicao:
                    page.evaluate("window.scrollTo(0, 800);")
                elif "4" in posicao or "lateral" in posicao:
                    page.evaluate("window.scrollTo(0, 500);")
                elif "5" in posicao or "rodape" in posicao:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                elif "6" in posicao or "7" in posicao or "materia" in posicao:
                    page.evaluate("window.scrollTo(0, 1100);")

                page.wait_for_timeout(2000)

                nome_arquivo = f"{cliente}_Espaco_{posicao}_{hoje}.png".replace(" ", "_").replace("/", "-")
                caminho_local = os.path.join("prints", nome_arquivo)

                page.screenshot(path=caminho_local, full_page=False)

                data_hora_agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                adicionar_carimbo_url_data(caminho_local, url, data_hora_agora, cliente, posicao)

                prints_gerados.append(caminho_local)

            except Exception as e:
                print(f"Erro ao capturar {cliente}: {e}")

        browser.close()

    enviar_email_com_anexos(prints_gerados, hoje)

if __name__ == "__main__":
    executar()
