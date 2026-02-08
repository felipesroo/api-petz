from fastapi import FastAPI
from playwright.async_api import async_playwright
import json

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Robô Petz Online 🐶 v2"}

@app.get("/scrape")
async def rodar_robo():
    print("Iniciando scrape...")
    async with async_playwright() as p:
        # Lança navegador com argumentos extras para evitar detecção e erros de memória
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled', # TRUQUE: Esconde que é automação
                '--disable-dev-shm-usage'
            ]
        )
        
        # Contexto com Viewport maior (para garantir que o site carregue o layout desktop)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        lista_produtos = []
        try:
            print("Acessando site...")
            await page.goto("https://www.petz.com.br/cachorro/racao/racao-seca", timeout=90000)

            # Espera inteligente: aguarda o site parar de carregar rede por pelo menos 1s
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass # Se estourar o tempo, segue a vida

            # Scroll mais lento e mais longo
            print("Rolando página...")
            for _ in range(4): 
                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(4000) # AUMENTEI PARA 4 SEGUNDOS

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

                    # Plano B para imagem se o JSON falhar
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
            
            # SE NÃO ACHOU NADA, AVISA!
            if len(lista_produtos) == 0:
                # Tira um print do título da página para saber se foi bloqueado
                titulo = await page.title()
                return [{"erro": "Nenhum produto encontrado", "titulo_pagina": titulo, "motivo": "Site lento ou bloqueio"}]

        except Exception as e:
            return [{"erro": f"Erro interno: {str(e)}"}]
            
        await browser.close()
        return lista_produtos
