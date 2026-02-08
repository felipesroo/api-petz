from fastapi import FastAPI
from playwright.async_api import async_playwright
# Importa a camuflagem
from playwright_stealth import stealth_async
import json
import random
import asyncio

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Robô Petz Stealth Ativo 🥷"}

@app.get("/scrape")
async def rodar_robo():
    print("Iniciando modo Stealth...")
    async with async_playwright() as p:
        # Argumentos para remover avisos de automação do Chrome
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
        )
        
        # Cria contexto com permissões de geolocalização e viewport aleatório para parecer humano
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            permissions=['geolocation']
        )
        
        page = await context.new_page()
        
        # --- A MÁGICA DA CAMUFLAGEM AQUI ---
        await stealth_async(page)
        # -----------------------------------

        lista_produtos = []
        try:
            print("Acessando site...")
            # Headers extras para parecer requisição real
            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.google.com/"
            })

            await page.goto("https://www.petz.com.br/cachorro/racao/racao-seca", timeout=120000)

            # Espera carregar
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            # Scroll humanizado (varia o tempo)
            print("Rolando página...")
            for _ in range(4): 
                await page.mouse.wheel(0, random.randint(1000, 2000))
                await asyncio.sleep(random.uniform(2, 4))

            cards = await page.query_selector_all('ptz-card')
            print(f"Cards encontrados: {len(cards)}")

            for card in cards:
                try:
                    nome_el = await card.query_selector('.ptz-card-label-left')
                    nome = await nome_el.inner_text() if nome_el else "Sem Nome"

                    preco_el = await card.query_selector('.ptz-card-price')
                    preco = "0"
                    if preco_el:
                        txt = await preco_el.inner_text()
                        preco = txt.replace('R$', '').replace('A partir de', '').split('\n')[0].strip()

                    link = ""
                    imagem = ""
                    dados = await card.get_attribute('info-badges-list')
                    if dados:
                        j = json.loads(dados)
                        variacao = j.get('variations', [{}])[0]
                        url_p = variacao.get('url')
                        img_p = variacao.get('thumbnail')
                        link = "https://" + url_p if url_p else ""
                        imagem = img_p if img_p else ""

                    if not imagem:
                        img_tag = await card.query_selector('img')
                        if img_tag:
                            imagem = await img_tag.get_attribute('src')

                    lista_produtos.append({
                        "nome": nome.strip(),
                        "preco": preco,
                        "link": link,
                        "imagem": imagem
                    })
                except:
                    continue
            
            # Verificação de bloqueio
            if len(lista_produtos) == 0:
                titulo = await page.title()
                # Se ainda der bloqueio, retornamos o título para saber
                return [{"erro": "Bloqueado ou Vazio", "titulo_pagina": titulo}]

        except Exception as e:
            return [{"erro": f"Erro interno: {str(e)}"}]
            
        await browser.close()
        return lista_produtos
