from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import json

app = FastAPI()

# --- MANTENHA SUA CHAVE AQUI ---
API_KEY = "cf26a5bf4dba51e058af2258d6eb4b4f" 
# -------------------------------

@app.get("/")
def home():
    return {"status": "Robô Amazon Bestsellers Online 📦"}

@app.get("/scrape")
def rodar_robo():
    print("Iniciando raspagem Amazon...")
    
    # URL dos Mais Vendidos
    url_alvo = "https://www.amazon.com.br/gp/bestsellers/?ref_=nav_cs_bestsellers"
    
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br', 
        'render': 'false', # Amazon costuma funcionar bem sem render (mais rápido)
    }

    try:
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
        
        if r.status_code != 200:
            return [{"erro": f"Erro na API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_produtos = []
        
        # ESTRATÉGIA AMAZON: Buscar os cards do Grid de Mais Vendidos
        # Geralmente ficam dentro de uma div com id "gridItemRoot" ou classes específicas
        cards = soup.select('div[id="gridItemRoot"] div.zg-grid-general-faceout')
        
        if not cards:
            # Tenta seletor alternativo (Carrossel ou Lista antiga)
            cards = soup.select('div.a-carousel-card, div.zg-item-immersion')

        print(f"Cards encontrados: {len(cards)}")

        for card in cards:
            try:
                # 1. Título (Amazon usa classes dinâmicas, então pegamos pelo link)
                # Procura qualquer link dentro do card e pega o texto
                link_tag = card.select_one('a.a-link-normal')
                if not link_tag: continue
                
                # O Link
                href = link_tag.get('href')
                full_link = "https://www.amazon.com.br" + href if href and not href.startswith('http') else href
                
                # O Nome (Geralmente está num span ou div dentro do link)
                nome_tag = card.select_one('div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1, span.a-truncate-cut')
                if nome_tag:
                    nome = nome_tag.get_text(strip=True)
                else:
                    # Se não achar a classe específica, pega o texto do link
                    nome = link_tag.get_text(strip=True)

                # 2. Preço
                preco = "0"
                # Amazon usa classes como _cDEzb_p13n-sc-price_3mJ9Z
                preco_tag = card.select_one('span.p13n-sc-price, span._cDEzb_p13n-sc-price_3mJ9Z, span.a-color-price')
                if preco_tag:
                    preco = preco_tag.get_text(strip=True)
                
                # 3. Imagem
                imagem = ""
                img_tag = card.select_one('img')
                if img_tag:
                    imagem = img_tag.get('src')

                if nome and len(nome) > 3:
                    lista_produtos.append({
                        "nome": nome,
                        "preco": preco,
                        "link": full_link,
                        "imagem": imagem
                    })

            except Exception as e:
                continue

        if not lista_produtos:
            return [{"erro": "Nenhum produto encontrado. A Amazon mudou o layout.", "html_sample": str(soup)[:500]}]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
