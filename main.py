from fastapi import FastAPI
from playwright.async_api import async_playwright
import json

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Robô Petz Online 🐶"}

@app.get("/scrape")
async def rodar_robo():
    async with async_playwright() as p:
        # Lança navegador configurado para Docker/Servidor
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        lista_produtos = []
        try:
            print("Acessando Petz...")
            await page.goto("https://www.petz.com.br/cachorro/racao/racao-seca", timeout=60000)

            # Scroll rápido
            for _ in range(3): 
                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(2000)

            cards = await page.query_selector_all('ptz-card')

            for card in cards:
                try:
                    # Lógica de extração original
                    nome_el = await card.query_selector('.ptz-card-label-left')
                    nome = await nome_el.inner_text() if nome_el else "Sem Nome"

                    preco_el = await card.query_selector('.ptz-card-price')
                    preco = "0"
                    if preco_el:
                        txt = await preco_el.inner_text()
                        preco = txt.replace('R$', '').replace('A partir de', '').split('\n')[0].strip()

                    link = ""
                    dados = await card.get_attribute('info-badges-list')
                    if dados:
                        j = json.loads(dados)
                        variacao = j.get('variations', [{}])[0]
                        url_p = variacao.get('url')
                        img_p = variacao.get('thumbnail')
                        link = "https://" + url_p if url_p else ""
                        imagem = img_p if img_p else ""

                    lista_produtos.append({
                        "nome": nome.strip(),
                        "preco": preco,
                        "link": link,
                        "imagem": imagem
                    })
                except:
                    continue
            
        except Exception as e:
            return {"erro": str(e)}
            
        await browser.close()
        
        # RETORNA O JSON PARA QUEM CHAMOU (n8n)
        return lista_produtos