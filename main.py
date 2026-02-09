from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import json
import re

app = FastAPI()

# --- SUA CHAVE AQUI ---
API_KEY = "cf26a5bf4dba51e058af2258d6eb4b4f" 
# ----------------------

@app.get("/")
def home():
    return {"status": "Robô Petz Outlet Online 🐶"}

@app.get("/scrape")
def rodar_robo():
    # URL da Outlet Petz
    url_alvo = "https://www.petz.com.br/colecao/UT-outlet-petz"
    
    print(f"Iniciando raspagem na Outlet: {url_alvo}")
    
    # Configuração para Petz (render=true ajuda a carregar o JSON dinâmico se precisar)
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br',
        'device_type': 'desktop', # Desktop costuma trazer mais dados no JSON da Petz
        'premium': 'true',        # Ajuda a evitar bloqueios de IP
        'render': 'true'         # Tente false primeiro (mais rápido). Se vier vazio, mude para true.
    }

    try:
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
        
        if r.status_code != 200:
            return [{"erro": f"Erro API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_produtos = []
        
        # --- ESTRATÉGIA 1: JSON-LD (Dados Ocultos) ---
        # A Petz organiza tudo bonitinho aqui para o Google
        scripts = soup.find_all('script', type='application/ld+json')
        
        print(f"Scripts JSON encontrados: {len(scripts)}")
        
        for script in scripts:
            try:
                dados = json.loads(script.string)
                
                # Procura pela lista de produtos (ItemList)
                if isinstance(dados, dict) and dados.get('@type') == 'ItemList':
                    items = dados.get('itemListElement', [])
                    
                    for item in items:
                        produto = item.get('item', {})
                        
                        # Extração Direta do JSON
                        nome = produto.get('name')
                        url = produto.get('url')
                        imagem = produto.get('image', '')
                        if isinstance(imagem, list): imagem = imagem[0] # Pega a primeira foto
                        
                        # Preço (Geralmente em 'offers')
                        oferta = produto.get('offers', {})
                        preco_num = oferta.get('price')
                        if preco_num:
                            preco = f"R$ {str(preco_num).replace('.', ',')}"
                        else:
                            preco = "Ver no site"

                        # Correção de URL relativa
                        if url and not url.startswith('http'):
                            url = "https://www.petz.com.br" + url

                        if nome and url:
                            lista_produtos.append({
                                "nome": nome,
                                "preco": preco,
                                "link": url,
                                "imagem": imagem,
                                "origem": "JSON"
                            })
            except:
                continue

        # --- ESTRATÉGIA 2: VARREDURA VISUAL (Fallback) ---
        # Se o JSON falhar, usamos a técnica de "varrer links" que aprendemos na Amazon
        if not lista_produtos:
            print("JSON vazio, ativando modo visual...")
            links = soup.select('a[href*="/produto/"]')
            
            ids_processados = set()
            
            for link in links:
                try:
                    href = link.get('href')
                    if not href or href in ids_processados: continue
                    ids_processados.add(href)
                    
                    full_link = "https://www.petz.com.br" + href if not href.startswith('http') else href
                    
                    # Sobe para achar o Card
                    card = link.find_parent('div', class_=lambda x: x and ('card' in x or 'product' in x))
                    if not card: card = link.find_parent('li')
                    
                    if not card: continue

                    # Nome
                    nome = "Produto Petz"
                    nome_tag = card.find(['h3', 'h2', 'span'], class_=lambda x: x and 'name' in x)
                    if nome_tag: 
                        nome = nome_tag.get_text(strip=True)
                    else:
                        img = card.find('img')
                        if img and img.get('alt'): nome = img.get('alt')

                    # Preço
                    preco = "Ver no site"
                    preco_tag = card.find(string=re.compile(r'R\$\s?

