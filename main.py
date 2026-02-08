from fastapi import FastAPI
from playwright.async_api import async_playwright
import json
import random
import asyncio
import re

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Robô Petz V4 (Detetive) 🕵️"}

@app.get("/scrape")
async def rodar_robo():
    print("Iniciando modo Detetive...")
    async with async_playwright() as p:
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
        
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768}, # Resolução padrão de notebook
            locale='pt-BR',
            timezone_id='America/Sao_Paulo'
        )
        
        page = await context.new_page()
        
        # Camuflagem Manual
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        lista_produtos = []
        try:
            print("Acessando site...")
            await page.goto("https://www.petz.com.br/cachorro/racao/racao-seca", timeout=90000)

            # Espera um pouco mais para garantir que os preços carreguem
            await page.wait_for_timeout(5000)

            print("Rolando página...")
            for _ in range(3): 
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)

            # ESTRATÉGIA NOVA: Pegar todos os links de produtos
            # A Petz geralmente usa tags <a> com links que contém '/produto/'
            cards = await page.query_selector_all('a[href*="/produto/"]')
            print(f"Links de produtos encontrados: {len(cards)}")

            links_visitados = set()

            for card in cards:
                try:
                    # 1. Extrair Link
                    link_relativo = await card.get_attribute('href')
                    if not link_relativo: continue
                    
                    full_link = "https://www.petz.com.br" + link_relativo if not link_relativo.startswith('http') else link_relativo
                    
                    # Evita duplicatas (o site tem vários links pro mesmo produto)
                    if full_link in links_visitados:
                        continue
                    links_visitados.add(full_link)

                    # 2. Extrair Texto Completo do Card (Nome e Preço costumam estar dentro do link ou perto)
                    texto_completo = await card.inner_text()
                    
                    # Se o texto do link for muito curto, tentamos pegar o elemento pai (o card inteiro)
                    if len(texto_completo) < 10:
                        pai = await card.query_selector('xpath=..') # Sobe um nível
                        if pai:
                            texto_completo = await pai.inner_text()

                    # 3. Processar Nome (Geralmente é a primeira linha ou texto longo)
                    linhas = [l for l in texto_completo.split('\n') if len(l) > 3]
                    nome = linhas[0] if linhas else "Nome não detectado"
                    
                    # Tenta limpar termos comuns que não são nome
                    if "R$" in nome or "%" in nome:
                         # Se a primeira linha for preço, tenta a segunda
                         nome = linhas[1] if len(linhas) > 1 else nome

                    # 4. Processar Preço (Procura por R$)
                    preco = "Esgotado/Sem Preço"
                    # Regex para achar valor monetário: R$ 100,00
                    match = re.search(r'R\$\s?(\d+[\.,]\d{2})', texto_completo)
                    if match:
                        preco = match.group(1)
                    
                    # 5. Imagem (Procura tag img dentro)
                    imagem = ""
                    img_tag = await card.query_selector('img')
                    if img_tag:
                        imagem = await img_tag.get_attribute('src')
                    
                    # Só adiciona se tiver nome válido
                    if nome and "Nome não detectado" not in nome:
                        lista_produtos.append({
                            "nome": nome.strip(),
                            "preco": preco,
                            "link": full_link,
                            "imagem": imagem
                        })

                except Exception as e:
                    continue
            
            if len(lista_produtos) == 0:
                 return [{"erro": "Site carregou mas seletor falhou. Estrutura mudou."}]

        except Exception as e:
            return [{"erro": f"Erro interno: {str(e)}"}]
            
        await browser.close()
        return lista_produtos[:50] # Limita a 50 itens para não travar
