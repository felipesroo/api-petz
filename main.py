from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import json
import time

app = FastAPI()

# --- SUA CHAVE AQUI ---
API_KEY = "SUA_CHAVE_DA_SCRAPERAPI_AQUI" 
# ----------------------

@app.get("/")
def home():
    return {"status": "Robô Petz Híbrido Online 🚀"}

@app.get("/scrape")
def rodar_robo():
    print("Iniciando raspagem...")
    
    # URL da categoria
    url_alvo = "https://www.petz.com.br/cachorro/racao/racao-seca"
    
    # Configuração Otimizada do ScraperAPI
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br', # IP Brasileiro
        'render': 'false',    # DESLIGADO: Mais rápido e menos bugs visuais
        'keep_headers': 'true' # Mantém nossos headers para parecer humano
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 1. Faz o pedido
        r = requests.get('http://api.scraperapi.com', params=payload, headers=headers, timeout=60)
        
        if r.status_code != 200:
            return [{"erro": f"Erro na API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_produtos = []
        
        # 2. ESTRATÉGIA SNIPER: Buscar JSON-LD (Dados Estruturados)
        # A Petz entrega os dados prontos para o Google neste script
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                dados = json.loads(script.string)
                # Verifica se é uma lista de produtos
                if isinstance(dados, dict) and dados.get('@type') == 'ItemList':
                    items = dados.get('itemListElement', [])
                    for item in items:
                        produto = item.get('item', {})
                        nome = produto.get('name')
                        url = produto.get('url')
                        
                        # Preço e Imagem as vezes estão em locais diferentes no JSON
                        oferta = produto.get('offers', {})
                        preco = oferta.get('price', 'Ver no site') if isinstance(oferta, dict) else '0'
                        imagem = produto.get('image', '')
                        if isinstance(imagem, list): imagem = imagem[0]

                        if url and not url.startswith('http'):
                            url = "https://www.petz.com.br" + url

                        if nome:
                            lista_produtos.append({
                                "nome": nome,
                                "preco": str(preco),
                                "link": url,
                                "imagem": imagem
                            })
            except:
                continue

        # 3. PLANO B: Se o JSON falhar, busca visualmente (Links)
        if not lista_produtos:
            print("JSON vazio, tentando visual...")
            links = soup.select('a[href*="/produto/"]')
            links_unicos = set()
            
            for link in links:
                href = link.get('href')
                if href and href not in links_unicos:
                    links_unicos.add(href)
                    
                    # Tenta achar o preço perto do link
                    card = link.find_parent('div')
                    texto_card = card.get_text() if card else link.get_text()
                    
                    if "R$" in texto_card:
                        # Extrai preço grosseiramente
                        preco = "R$ " + texto_card.split('R$')[1].split(' ')[0]
                    else:
                        preco = "Ver no site"
                        
                    lista_produtos.append({
                        "nome": "Produto Detectado (Visual)",
                        "preco": preco,
                        "link": "https://www.petz.com.br" + href if not href.startswith('http') else href,
                        "imagem": ""
                    })

        # DEBUG FINAL: Se ainda estiver vazio, mostra o Título da página para sabermos onde caiu
        if not lista_produtos:
            titulo = soup.title.string if soup.title else "Sem Título"
            return [{
                "erro": "Nenhum produto encontrado", 
                "titulo_pagina": titulo, # Isso vai nos dizer se caiu em 'Block', 'Notify Me' ou outra coisa
                "html_inicio": str(soup)[:300]
            }]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
