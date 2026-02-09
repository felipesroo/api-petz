from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# --- COLOQUE SUA CHAVE AQUI ---
API_KEY = "cf26a5bf4dba51e058af2258d6eb4b4f"
# ------------------------------

@app.get("/")
def home():
    return {"status": "Robô Amazon Mobile V2 Online 📦"}

@app.get("/scrape")
def rodar_robo():
    print("Iniciando raspagem Amazon Mobile...")
    
    url_alvo = "https://www.amazon.com.br/gp/bestsellers/?ref_=nav_cs_bestsellers"
    
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br', 
        'device_type': 'mobile', # TRUQUE: Acessar como celular
        'premium': 'true',       # TRUQUE: Usar IPs residenciais premium
    }

    try:
        # Timeout maior porque IPs premium demoram um pouco mais
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=90)
        
        if r.status_code != 200:
            return [{"erro": f"Erro ScraperAPI: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_produtos = []
        
        # ESTRATÉGIA MOBILE:
        # No mobile, a Amazon usa uma lista vertical.
        # Procuramos por containers de itens (divs com classe 'zg-item')
        # Ou procuramos links genéricos de produtos
        
        # Tenta pegar os cards pelo Grid padrão de Bestsellers
        cards = soup.select('div#gridItemRoot, div.zg-grid-general-faceout, div.p13n-sc-uncoverable-faceout')
        
        if not cards:
             # Se falhar, tenta pegar qualquer link que tenha /dp/ (padrão de produto Amazon)
             print("Seletores de grid falharam, tentando links diretos...")
             links_produtos = soup.select('a[href*="/dp/"]')
             # Transforma links em "cards" falsos para processar igual
             cards = [l.find_parent('div') for l in links_produtos if l.find_parent('div')]

        print(f"Possíveis produtos encontrados: {len(cards)}")

        produtos_unicos = set()

        for card in cards:
            if not card: continue
            try:
                # 1. Título (Pode estar em várias tags diferentes)
                nome_tag = card.select_one('span.p13n-sc-truncate, div.p13n-sc-truncate-desktop-type2, span._cDEzb_p13n-sc-css-line-clamp-3_g3dy1')
                
                # Se não achou tag de nome, tenta achar qualquer imagem e pegar o 'alt'
                if not nome_tag:
                    img = card.select_one('img')
                    nome = img.get('alt') if img else "Sem Nome"
                else:
                    nome = nome_tag.get_text(strip=True)

                # 2. Link
                link_tag = card.select_one('a.a-link-normal')
                if not link_tag: 
                    # Se o próprio card for um link (comum no mobile)
                    if card.name == 'a': link_tag = card
                    else: continue
                
                href = link_tag.get('href')
                if not href: continue
                
                full_link = "https://www.amazon.com.br" + href if not href.startswith('http') else href

                # Evita duplicatas
                if full_link in produtos_unicos: continue
                produtos_unicos.add(full_link)

                # 3. Preço
                preco = "Ver no site"
                # Amazon adora mudar essa classe. Buscamos classes que contenham 'price'
                preco_tag = card.select_one('span._cDEzb_p13n-sc-price_3mJ9Z, span.p13n-sc-price, span.a-color-price')
                if preco_tag:
                    preco = preco_tag.get_text(strip=True)

                # 4. Imagem
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

            except Exception:
                continue

        if not lista_produtos:
            # DEBUG: Mostra o título para saber se fomos bloqueados
            titulo = soup.title.get_text() if soup.title else "Sem Título"
            return [{"erro": "Bloqueio Amazon ou Layout mudou", "titulo_pagina": titulo, "html_inicio": str(soup)[:200]}]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
