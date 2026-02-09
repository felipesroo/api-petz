from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import re
import time

app = FastAPI()

# --- SUA CHAVE AQUI ---
API_KEY = "cf26a5bf4dba51e058af2258d6eb4b4f" 
# ----------------------

@app.get("/")
def home():
    return {"status": "Robô Ofertas do Dia Online 🏷️"}

@app.get("/scrape")
def rodar_robo():
    # URL Exata das Ofertas do Dia
    base_url = "https://www.amazon.com.br/s?k=ofertas+do+dia&__mk_pt_BR=%C3%85M%C3%85%C5%BD%C3%95%C3%91&crid=2ZJ0E5VVQA848&sprefix=ofertas+do+di%2Caps%2C234&ref=nb_sb_noss_2"
    
    # Quantidade de páginas para ler
    MAX_PAGINAS = 3
    
    lista_global = []
    print(f"Iniciando busca de 'Ofertas do Dia' ({MAX_PAGINAS} Páginas)...")

    for pagina in range(1, MAX_PAGINAS + 1):
        print(f"--- Processando Página {pagina} ---")
        
        # Lógica de Paginação
        if pagina == 1:
            url_atual = base_url
        else:
            url_atual = f"{base_url}&page={pagina}"
        
        payload = {
            'api_key': API_KEY, 
            'url': url_atual, 
            'country_code': 'br',
            'device_type': 'mobile', 
            'premium': 'true',       
            'render': 'false'        
        }

        try:
            r = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
            
            if r.status_code != 200:
                print(f"Pulo na pág {pagina} (Erro {r.status_code})")
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Procura os containers de resultado de busca
            cards = soup.select('div[data-component-type="s-search-result"]')
            
            # Backup: Se não achar os containers, procura links diretos
            if not cards:
                links = soup.select('a[href*="/dp/"]')
                cards = []
                seen_cards = set()
                for l in links:
                    pai = l.find_parent('div')
                    if pai and pai not in seen_cards:
                         cards.append(pai)
                         seen_cards.add(pai)

            print(f"  > Itens encontrados na pág {pagina}: {len(cards)}")
            
            novos = 0
            ids_vistos = set()

            for card in cards:
                try:
                    if not card: continue

                    # 1. Link e ID do Produto
                    link_tag = card.find('a', href=re.compile(r'/dp/'))
                    if not link_tag: continue
                    
                    href = link_tag.get('href')
                    match = re.search(r'/dp/([A-Z0-9]{10})', href)
                    if not match: continue
                    prod_id = match.group(1)

                    if prod_id in ids_vistos: continue
                    ids_vistos.add(prod_id)
                    
                    if any(p['link'].endswith(prod_id) for p in lista_global): continue

                    full_link = f"https://www.amazon.com.br/dp/{prod_id}"

                    # 2. Nome
                    nome = "Oferta Amazon"
                    img = card.find('img')
                    h2 = card.find('h2')
                    
                    if h2: 
                        nome = h2.get_text(strip=True)
                    elif img and img.get('alt'):
                        nome = img.get('alt')

                    # 3. Preço (CORRIGIDO AQUI)
                    preco = "Ver no site"
                    price_tag = card.select_one('.a-price .a-offscreen')
                    
                    if price_tag:
                        preco = price_tag.get_text(strip=True)
                    else:
                        whole = card.select_one('.a-price-whole')
                        frac = card.select_one('.a-price-fraction')
                        if whole:
                            v = whole.get_text(strip=True).replace('.', '')
                            # A LINHA QUE ESTAVA DANDO ERRO AGORA ESTÁ COMPLETA ABAIXO:
                            c = frac.get_text(strip=True) if frac else "00"
                            preco = f"R$ {v},{c}"

                    # 4. Imagem
                    imagem = img.get('src') if img else ""
                    
                    # 5. Desconto
                    desconto = ""
                    texto_card = card.get_text().lower()
                    match_desc = re.search(r'(\d+)%\s?(off|de desconto)', texto_card)
                    if match_desc:
                        desconto = f"-{match_desc.group(1)}%"

                    if "R$" in preco:
                        lista_global.append({
                            "pagina": pagina,
                            "nome": nome,
                            "preco": preco,
                            "desconto": desconto,
                            "link": full_link,
                            "imagem": imagem
