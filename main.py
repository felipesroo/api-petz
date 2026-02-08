from fastapi import FastAPI
from playwright.async_api import async_playwright
import json
import asyncio

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Robô Petz Sniper Ativo 🎯"}

@app.get("/scrape")
async def rodar_robo():
    print("Iniciando modo Sniper (JSON-LD)...")
    async with async_playwright() as p:
        # Lança navegador VISÍVEL para você ver se está abrindo
        # Se funcionar, depois você muda headless=True
        browser = await p.chromium.launch(
            headless=True, # Mude para False se quiser ver a mágica
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
        )
        
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        # Camuflagem básica
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        lista_produtos = []
        try:
            print("Acessando site...")
            await page.goto("https://www.petz.com.br/cachorro/racao/racao-seca", timeout=60000)
            
            # Espera carregar
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            # ESTRATÉGIA SNIPER: Buscar dados estruturados (JSON-LD)
            # A Petz geralmente coloca os produtos num script hidden para o Google
            scripts = await page.query_selector_all('script[type="application/ld+json"]')
            print(f"Scripts JSON encontrados: {len(scripts)}")
            
            for script in scripts:
                try:
                    conteudo = await script.inner_text()
                    dados = json.loads(conteudo)
                    
                    # Procura por listas de produtos dentro do JSON
                    if isinstance(dados, dict) and dados.get('@type') == 'ItemList':
                        items = dados.get('itemListElement', [])
                        for item in items:
                            produto = item.get('item', {})
                            # Extrai dados limpos
                            nome = produto.get('name', 'Sem Nome')
                            url = produto.get('url', '')
                            # Preço as vezes vem em 'offers'
                            oferta = produto.get('offers', {})
                            preco = oferta.get('price', '0') if isinstance(oferta, dict) else '0'
                            imagem = produto.get('image', '')
                            
                            # Corrige URL se for relativa
                            if url and not url.startswith('http'):
                                url = "https://www.petz.com.br" + url

                            if nome and url:
                                lista_produtos.append({
                                    "nome": nome,
                                    "preco": str(preco),
                                    "link": url,
                                    "imagem": imagem
                                })
                except:
                    continue
            
            # PLANO B: Se o JSON falhar, tenta o seletor visual SUPER GENÉRICO
            if len(lista_produtos) == 0:
                print("JSON falhou, tentando visual...")
                # Pega qualquer CARD que tenha preço
                cards = await page.query_selector_all('div[class*="card"], li[class*="product"]')
                
                for card in cards:
                    texto = await card.inner_text()
                    if "R$" in texto:
                        # Pega o primeiro link que achar dentro do card
                        link_el = await card.query_selector('a')
                        link = await link_el.get_attribute('href') if link_el else ""
                        if link:
                            lista_produtos.append({
                                "nome": "Produto Detectado (Visual)",
                                "preco": "Ver no Site",
                                "link": "https://www.petz.com.br" + link,
                                "imagem": ""
                            })

            if len(lista_produtos) == 0:
                # DEBUG: Tira um print para você ver o que o robô está vendo
                await page.screenshot(path="debug_petz.png")
                titulo = await page.title()
                return [{"erro": "Bloqueio Total. Verifique debug_petz.png", "titulo": titulo}]

        except Exception as e:
            return [{"erro": f"Erro fatal: {str(e)}"}]
            
        await browser.close()
        return lista_produtos[:50]
