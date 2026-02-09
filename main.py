from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

# --- SUA CHAVE AQUI ---
API_KEY = "cf26a5bf4dba51e058af2258d6eb4b4f" 
# ----------------------

@app.get("/")
def home():
    return {"status": "Robô Ofertas Amazon (Preço Corrigido) 🏷️"}

@app.get("/scrape")
def rodar_robo():
    # Busca por ofertas na categoria Cozinha (pode mudar o 'i=' para outras)
    url_alvo = "https://www.amazon.com.br/s?k=ofertas+do+dia&__mk_pt_BR=%C3%85M%C3%85%C5%BD%C3%95%C3%91&crid=2ZJ0E5VVQA848&sprefix=ofertas+do+di%2Caps%2C234&ref=nb_sb_noss_2" 
    
    print(f"Buscando ofertas em: {url_alvo}")
    
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br',
        'device_type': 'mobile',
        'premium': 'true', 
        'render': 'false'
    }

    try:
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=90)
        
        if r.status_code != 200:
            return [{"erro": f"Erro API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_ofertas = []
        
        # Seleciona os cards de resultado da busca
        cards = soup.select('div[data-component-type="s-search-result"]')
        
        if not cards:
            links = soup.select('a[href*="/dp/"]')
            cards = [l.find_parent('div') for l in links if l.find_parent('div')]

        print(f"Produtos encontrados: {len(cards)}")
        
        links_visitados = set()

        for card in cards:
            try:
                if not card: continue

                # 1. Link e ID
                link_tag = card.find('a', href=re.compile(r'/dp/'))
                if not link_tag: continue

                href = link_tag.get('href')
                match_id = re.search(r'/dp/([A-Z0-9]{10})', href)
                if not match_id: continue
                prod_id = match_id.group(1)

                if prod_id in links_visitados: continue
                links_visitados.add(prod_id)
                
                full_link = f"https://www.amazon.com.br/dp/{prod_id}"

                # 2. Nome
                nome = "Oferta"
                img = card.find('img')
                if img and img.get('alt'):
                    nome = img.get('alt')
                else:
                    h2 = card.find('h2')
                    if h2: nome = h2.get_text(strip=True)

                # --- 3. PREÇO (LÓGICA BLINDADA) ---
                preco = "Ver no site"
                
                # TENTATIVA 1: .a-offscreen (Melhor método)
                # Pega o preço formatado escondido (ex: R$ 19,90)
                price_offscreen = card.select_one('.a-price .a-offscreen')
                
                if price_offscreen:
                    preco = price_offscreen.get_text(strip=True)
                else:
                    # TENTATIVA 2: Montar manualmente (Inteiro + Fração)
                    # Caso o offscreen falhe, tenta pegar as partes visuais
                    price_whole = card.select_one('.a-price-whole')
                    price_fraction = card.select_one('.a-price-fraction')
                    
                    if price_whole:
                        valor = price_whole.get_text(strip=True).replace('.', '')
                        centavos = price_fraction.get_text(strip=True) if price_fraction else "00"
                        preco = f"R$ {valor},{centavos}"
                    else:
                        # TENTATIVA 3: Regex no texto do cartão (Último recurso)
                        # Busca padrão brasileiro: R$ 1.234,56
                        texto_full = card.get_text()
                        match_preco = re.search(r'R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{1,2}))', texto_full)
                        if match_preco: 
                            preco = match_preco.group(0)

                # 4. Desconto
                desconto = ""
                # Procura texto "20% off" ou similar
                texto_card = card.get_text().lower()
                match_desc = re.search(r'(\d+)%\s?(off|de desconto)', texto_card)
                if match_desc:
                    desconto = f"-{match_desc.group(1)}%"

                imagem = img.get('src') if img else ""

                lista_ofertas.append({
                    "nome": nome,
                    "preco": preco,
                    "desconto": desconto,
                    "link": full_link,
                    "imagem": imagem
                })

            except:
                continue

        if not lista_ofertas:
            return [{"erro": "Nenhuma oferta encontrada.", "titulo": soup.title.string if soup.title else "Sem Título"}]

        return lista_ofertas[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
