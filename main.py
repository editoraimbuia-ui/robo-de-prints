"""
Monitor de Prints - Gazeta do Paraná
Roda no GitHub Actions (Linux + Playwright)
Busca banner pelo atributo alt, fotografa o elemento, envia por email.
"""

import json
import os
import smtplib
from datetime import date, datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

EMAIL_REMETENTE = "editoraimbuia@gmail.com"
EMAIL_DESTINO   = "gazetadoparana01@hotmail.com"
GMAIL_SENHA     = os.environ.get("GMAIL_SENHA", "")

CAMPANHAS_JSON = Path(__file__).parent / "campanhas.json"
URL_SITE = "https://www.gazetadoparana.com.br"


def carregar_campanhas():
    if not CAMPANHAS_JSON.exists():
        print("[ERRO] campanhas.json não encontrado")
        return []
    with open(CAMPANHAS_JSON, encoding="utf-8") as f:
        return json.load(f)


def campanha_ativa_hoje(c):
    if not c.get("ativo", True):
        return False
    hoje = date.today()
    try:
        inicio = date.fromisoformat(c["inicio"])
        fim    = date.fromisoformat(c["fim"])
    except Exception:
        return False
    return inicio <= hoje <= fim


def adicionar_carimbo(img_bytes, campanha, posicao):
    from io import BytesIO
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    rodape_h = 36
    nova = Image.new("RGB", (img.width, img.height + rodape_h), (30, 30, 30))
    nova.paste(img, (0, 0))
    draw = ImageDraw.Draw(nova)
    try:
        fonte = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        fonte = ImageFont.load_default()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    texto = f"{URL_SITE}  |  {agora}  |  {campanha}  |  {posicao}"
    draw.text((8, img.height + 8), texto, fill=(220, 220, 220), font=fonte)
    buf = BytesIO()
    nova.save(buf, format="PNG")
    return buf.getvalue()


def tirar_print_banner(page, alt_texto, nome_arquivo):
    if not alt_texto or alt_texto.strip() == "":
        print(f"  [AVISO] alt vazio, pulando {nome_arquivo}")
        return None
    seletores = [
        f'img[alt="{alt_texto}"]',
        f'img[alt*="{alt_texto}"]',
        f'[alt="{alt_texto}"]',
    ]
    for sel in seletores:
        try:
            elem = page.locator(sel).first
            if elem.count() == 0:
                continue
            elem.scroll_into_view_if_needed(timeout=5000)
            page.wait_for_timeout(800)
            dados = elem.screenshot()
            if dados and len(dados) > 1000:
                print(f"  [OK] Banner encontrado: {sel}")
                return dados
            pai = page.locator(sel).first.locator("xpath=..")
            dados = pai.screenshot()
            if dados and len(dados) > 1000:
                print(f"  [OK] Banner (pai) encontrado: {sel}")
                return dados
        except Exception as e:
            print(f"  [tentativa] {sel}: {e}")
            continue
    print(f"  [AVISO] Banner nao encontrado. Print completo da pagina.")
    return page.screenshot(full_page=False)


def enviar_email(assunto, corpo, anexos):
    if not GMAIL_SENHA:
        print("[ERRO] GMAIL_SENHA nao definida nos Secrets do GitHub.")
        return False
    msg = MIMEMultipart()
    msg["From"]    = EMAIL_REMETENTE
    msg["To"]      = EMAIL_DESTINO
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo, "plain", "utf-8"))
    for nome_arquivo, dados in anexos:
        img_part = MIMEImage(dados, name=nome_arquivo)
        img_part.add_header("Content-Disposition", "attachment", filename=nome_arquivo)
        msg.attach(img_part)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_REMETENTE, GMAIL_SENHA)
            smtp.sendmail(EMAIL_REMETENTE, EMAIL_DESTINO, msg.as_bytes())
        print(f"  [OK] Email enviado para {EMAIL_DESTINO}")
        return True
    except Exception as e:
        print(f"  [ERRO] Falha ao enviar email: {e}")
        return False


def main():
    campanhas = carregar_campanhas()
    hoje = date.today()
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    ativas = [c for c in campanhas if campanha_ativa_hoje(c)]
    print(f"[{agora_str}] {len(ativas)} campanha(s) ativa(s) hoje ({hoje})")
    if not ativas:
        print("Nenhuma campanha para processar. Encerrando.")
        return
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-gpu","--window-size=1920,1080"],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        for c in ativas:
            nome = c.get("nome", f"campanha_{c.get('id',0)}")
            print(f"\n-- Processando: {nome} --")
            page = context.new_page()
            try:
                page.goto(URL_SITE, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  [ERRO] Nao foi possivel abrir o site: {e}")
                page.close()
                continue
            anexos = []
            data_str = hoje.strftime("%Y%m%d")
            if c.get("topo", False) and c.get("banner_topo", "").strip():
                alt = c["banner_topo"]
                fname = f"topo_{nome}_{data_str}.png"
                print(f"  Topo -> alt: '{alt}'")
                dados = tirar_print_banner(page, alt, fname)
                if dados:
                    dados = adicionar_carimbo(dados, nome, "Topo")
                    anexos.append((fname, dados))
            if c.get("meio", False) and c.get("banner_meio", "").strip():
                alt = c["banner_meio"]
                fname = f"meio_{nome}_{data_str}.png"
                print(f"  Meio -> alt: '{alt}'")
                dados = tirar_print_banner(page, alt, fname)
                if dados:
                    dados = adicionar_carimbo(dados, nome, "Meio")
                    anexos.append((fname, dados))
            page.close()
            if not anexos:
                print(f"  [AVISO] Nenhum print gerado para '{nome}' - verifique o campo alt.")
                continue
            assunto = f"Comprovante de veiculacao - {nome} - {hoje.strftime('%d/%m/%Y')}"
            corpo = (
                f"Ola,\n\nSeguem os prints de comprovacao de veiculacao da campanha '{nome}' "
                f"no site gazetadoparana.com.br, capturados em {agora_str}.\n\n"
                f"Periodo da campanha: {c.get('inicio')} a {c.get('fim')}\n\n"
                f"Atenciosamente,\nEditora Imbuia"
            )
            enviar_email(assunto, corpo, anexos)
        browser.close()
    print("\n[FIM] Processamento concluido.")


if __name__ == "__main__":
    main()
