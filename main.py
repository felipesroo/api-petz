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
    return {"status": "Robô Petz Outlet (Render JS) Online ⚡"}

@app.get("/scrape")
def rodar_robo():
    url_alvo = "https://www.petz.com.br/colecao/UT-outlet-petz"
    
    print(f"Iniciando raspagem com RENDER: {url_alvo}")
    
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br',
        'device_type': 'desktop', 
        'premium': 'true',        
        'render': 'true' # OBRIGATÓRIO: Liga o JavaScript para carregar os produtos
    }

    try:
        # Timeout aumentado para 90s porque renderizar demora mais
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=90)
        
        if r.status_code != 200:
            return [{"erro": f"Erro API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_produtos = []
        
        # --- ESTRATÉGIA 1: TENTAR JSON-LD (Geralmente aparece com render=true) ---
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                dados = json.loads(script.string)
                if isinstance(dados, dict) and dados.get('@type') == 'ItemList':
                    items = dados.get('itemListElement', [])
                    for item in items:
                        produto = item.get('item', {})
                        nome = produto.get('name')
                        url = produto.get('url')
                        img = produto.get('image', '')
                        if isinstance(img, list): img = img[0]
                        
                        oferta = produto.get('offers', {})
                        preco = oferta.get('price')
                        if preco: preco = f"R$ {str(preco).replace('.', ',')}"
                        else: preco = "Ver no site"

                        if url and not url.startswith('http'):
                            url = "https://www.petz.com.br" + url

                        if nome and url:
                            lista_produtos.append({
                                "nome": nome,
                                "preco": str(preco),
                                "link": url,
                                "imagem": img,
                                "origem": "JSON"
                            })
            except:
                continue

        # --- ESTRATÉGIA 2: SCANNER UNIVERSAL (Se o JSON falhar) ---
        # Ignora classes CSS e busca por links de produtos (/produto/)
        if not lista_produtos:
            print("JSON falhou, ativando Scanner Universal...")
            links = soup.select('a[href*="/produto/"]')
            ids_processados = set()

            for link in links:
                try:
                    href = link.get('href')
                    if not href: continue
                    
                    # Evita duplicatas
                    if href in ids_processados: continue
                    ids_processados.add(href)
                    
                    full_link = "https://www.petz.com.br" + href if not href.startswith('http') else href
                    
                    # Sobe na árvore HTML para achar o bloco do produto
                    # Tenta achar o container pai (div ou li)
                    card = link.find_parent('div')
                    if not card: card = link.find_parent('li')
                    if not card: continue

                    # 1. Nome (Busca imagem com alt ou texto do link)
                    nome = "Produto Petz"
                    img_tag = card.find('img')
                    if img_tag and img_tag.get('alt'):
                        nome = img_tag.get('alt')
                    else:
                        h3 = card.find(['h3', 'h2', 'h1'])
                        if h3: nome = h3.get_text(strip=True)
                        else: nome = link.get_text(strip=True)

                    # 2. Preço (Regex para achar R$ XX,XX em qualquer lugar do card)
                    preco = "Ver no site"
                    texto_completo = card.get_text()
                    match_preco = re.search(r'R\$\s?(\d+[\.,]\d{2})', texto_completo)
                    if match_preco:
                        preco = match_preco.group(0)

                    # 3. Imagem
                    imagem = ""
                    if img_tag:
                        imagem = img_tag.get('src') or img_tag.get('data-src')

                    # Só salva se tiver cara de produto (preço ou imagem)
                    if len(nome) > 3 and ("R$" in preco or imagem):
                        lista_produtos.append({
                            "nome": nome,
                            "preco": preco,
                            "link": full_link,
                            "imagem": imagem,
                            "origem": "Visual Universal"
                        })
                except:
                    continue

        if not lista_produtos:
            # Debug: Mostra o título para sabermos se a página carregou
            return [{"erro": "Nenhum produto encontrado.", "titulo": soup.title.string if soup.title else "Sem Título"}]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
