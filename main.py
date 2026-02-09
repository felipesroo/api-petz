from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

# --- SUA CHAVE AQUI (Com as aspas!) ---
API_KEY = "cf26a5bf4dba51e058af2258d6eb4b4f" 
# --------------------------------------

@app.get("/")
def home():
    return {"status": "Robô Amazon Cozinha Online 🍳"}

@app.get("/scrape")
def rodar_robo():
    # URL Específica da Categoria Cozinha
    url_alvo = "https://www.amazon.com.br/gp/bestsellers/kitchen/ref=zg_bs_kitchen_sm"
    
    print(f"Iniciando raspagem em: {url_alvo}")
    
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br',
        'device_type': 'mobile', # Mobile é o segredo para listas longas
    }

    try:
        # Timeout de 60s é seguro para ScraperAPI
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
        
        if r.status_code != 200:
            return [{"erro": f"Erro API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_produtos = []
        
        # ESTRATÉGIA UNIVERSAL (Varrer Links /dp/)
        # Isso funciona mesmo se a Amazon mudar o layout amanhã
        links_produtos = soup.select('a[href*="/dp/"]')
        
        print(f"Links brutos encontrados: {len(links_produtos)}")
        
        links_visitados = set()

        for link in links_produtos:
            try:
                href = link.get('href')
                
                # Limpeza e Extração do ID do Produto (ASIN)
                if not href: continue
                match_id = re.search(r'/dp/([A-Z0-9]{10})', href)
                if not match_id: continue
                prod_id = match_id.group(1)
                
                # Evita duplicatas (Amazon repete links na mesma página)
                if prod_id in links_visitados: continue
                links_visitados.add(prod_id)
                
                full_link = f"https://www.amazon.com.br/dp/{prod_id}"

                # Sobe na árvore do HTML para achar o "Cartão" do produto
                # Tenta achar o container pai que tem as informações
                card = link.find_parent('div', class_=lambda x: x and 'zg' in x) 
                if not card: card = link.find_parent('li')
                if not card: card = link.find_parent('div') 

                if not card: continue

                # 1. Extração de Nome
                nome = "Nome não detectado"
                img = card.find('img')
                if img and img.get('alt'):
                    nome = img.get('alt')
                else:
                    # Plano B: Texto do link ou do card
                    texto_card = card.get_text(" ", strip=True)
                    if len(texto_card) > 5:
                         nome = texto_card[:60] + "..." # Pega o início do texto

                # 2. Extração de Preço
                preco = "Ver no site"
                texto_completo = card.get_text()
                # Regex para achar R$ 123,45
                match_preco = re.search(r'R\$\s?(\d+[\.,]\d{2})', texto_completo)
                if match_preco:
                    preco = match_preco.group(0)

                # 3. Extração de Imagem
                imagem = ""
                if img: imagem = img.get('src')

                lista_produtos.append({
                    "nome": nome,
                    "preco": preco,
                    "link": full_link,
                    "imagem": imagem
                })

            except:
                continue

        if not lista_produtos:
            return [{
                "erro": "Nenhum produto encontrado.", 
                "titulo_pagina": soup.title.string if soup.title else "Sem Título"
            }]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
