import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

API_URL = "https://script.google.com/macros/s/AKfycbxBXeDIie_Ler7HRrfQKMp1S-nr8NJNw-P8L8aCQr7Axtomizye0xpvSKu9EsMyrp2mkw/exec"

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

def executar_prints():
    os.makedirs("prints", exist_ok=True)
    hoje = datetime.now().date()
    
    try:
        response = requests.get(API_URL)
        campanhas = response.json()
    except Exception as e:
        print(f"Erro ao buscar planilha: {e}")
        campanhas = []

    falhas = []
    capturas_realizadas = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        for item in campanhas:
            status = str(item.get("status", "")).strip().upper()
            url = str(item.get("url", "")).strip()
            cliente = str(item.get("cliente", "Cliente")).strip()
            posicao = str(item.get("posicao", "")).strip()
            
            d_inicio = converter_data(item.get("data_inicio"))
            d_fim = converter_data(item.get("data_fim"))
            
            # Validação se hoje está dentro da janela de exibição
            dentro_do_prazo = True
            if d_inicio and hoje < d_inicio:
                dentro_do_prazo = False
            if d_fim and hoje > d_fim:
                dentro_do_prazo = False

            if status == "ATIVO" and url and dentro_do_prazo:
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                    
                sucesso = False
                
                # Tenta recarregar a página até 5 vezes para encontrar o banner rotativo
                for tentativa in range(5):
                    try:
                        print(f"Tentativa {tentativa+1} para {cliente} ({posicao}) em {url}")
                        page.goto(url, wait_until="networkidle", timeout=30000)
                        page.wait_for_timeout(3000)
                        
                        agora = datetime.now()
                        hora_str = agora.strftime("%H:%M")
                        data_str = agora.strftime("%d/%m/%Y")
                        data_arquivo = agora.strftime("%Y-%m-%d")
                        
                        # Injeta a moldura estilo Desktop (Navegador + Barra do Windows)
                        page.evaluate(f"""
                            () => {{
                                const topNav = document.createElement('div');
                                topNav.style.cssText = 'position:fixed;top:0;left:0;width:100%;background:#202124;color:#e8eaed;padding:8px 15px;font-size:13px;font-family:Arial,sans-serif;z-index:999999;box-sizing:border-box;display:flex;align-items:center;border-bottom:1px solid #3c4043;';
                                topNav.innerHTML = '<span style="color:#9aa0a6;margin-right:10px;">🔒</span><div style="background:#303134;padding:4px 12px;border-radius:16px;width:100%;color:#fff;font-size:12px;">{url}</div>';
                                document.body.appendChild(topNav);

                                const taskbar = document.createElement('div');
                                taskbar.style.cssText = 'position:fixed;bottom:0;left:0;width:100%;background:#101010;color:#ffffff;padding:4px 15px;font-size:11px;font-family:Arial,sans-serif;z-index:999999;box-sizing:border-box;display:flex;justify-content:space-between;align-items:center;height:40px;border-top:1px solid #222;';
                                taskbar.innerHTML = '<div><span style="margin-right:15px;font-weight:bold;">⊞ Iniciar</span><input type="text" value="Digite aqui para pesquisar" style="background:#222;border:none;color:#aaa;padding:3px 10px;border-radius:3px;font-size:11px;" readonly></div><div style="text-align:right;line-height:1.2;"><div>{hora_str}</div><div>{data_str}</div></div>';
                                document.body.appendChild(taskbar);
                                
                                document.body.style.paddingTop = '38px';
                                document.body.style.paddingBottom = '40px';
                            }}
                        """)
                        
                        page.wait_for_timeout(1000)
                        
                        cliente_limpo = "".join(c for c in cliente if c.isalnum() or c in (' ', '_', '-')).strip()
                        posicao_limpa = "".join(c for c in posicao if c.isalnum() or c in (' ', '_', '-')).strip()
                        nome_arquivo = f"prints/{cliente_limpo}_{posicao_limpa}_{data_arquivo}.png"
                        
                        page.screenshot(path=nome_arquivo, full_page=False)
                        sucesso = True
                        capturas_realizadas += 1
                        print(f"Print capturado com sucesso: {nome_arquivo}")
                        break
                    except Exception as e:
                        print(f"Tentativa {tentativa+1} falhou: {e}")
                
                if not sucesso:
                    falhas.append(f"Cliente: {cliente} ({posicao}) | URL: {url}")

        browser.close()

    if capturas_realizadas == 0 and not falhas:
        with open("prints/aviso.txt", "w") as f:
            f.write("Nenhuma campanha ATIVA e DENTRO DO PRAZO foi encontrada para hoje.")

    if falhas:
        print("::: ATENÇÃO: FALHA NOS PRINTS ABAIXO :::")
        for f in falhas:
            print(f)

if __name__ == "__main__":
    executar_prints()
