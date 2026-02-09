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
    return {"status": "Robô Ofertas Amazon Online 🏷️"}

@app.get("/scrape")
def rodar_robo():
    url_alvo = "https://www.amazon.com.br/s?k=ofertas&rh=p_n_deal_type%3A23565435011"
    
    print(f"Caçando ofertas em: {url_alvo}")
    
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br',
        'device_type': 'desktop', # Desktop às vezes mostra mais detalhes nas ofertas
        'premium': 'true', 
        'render': 'false' 
    }

    try:
        # Timeout de 90s para garantir
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=90)
        
        if r.status_code != 200:
            return [{"erro": f"Erro API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_ofertas = []
        
        # ESTRATÉGIA MISTA:
        # 1. Procura divs que têm a classe de 'deal' (oferta)
        # 2. Se não achar, usa a varredura de links /dp/
        
        # Tenta pegar os cards de oferta oficiais
        cards = soup.select('div[class*="DealCard"], div[class*="deal-card"], div[class*="Badge"]')
        
        # Se não achou cards específicos, pega qualquer container que tenha link de produto
        if not cards:
            print("Layout de cards não detectado, usando varredura de links...")
            links = soup.select('a[href*="/dp/"]')
            cards = [l.find_parent('div') for l in links if l.find_parent('div')]

        print(f"Potenciais ofertas encontradas: {len(cards)}")
        
        links_visitados = set()

        for card in cards:
            try:
                if not card: continue

                # --- 1. Link do Produto ---
                link_tag = card.find('a', href=re.compile(r'/dp/'))
                if not link_tag: 
                    # Tenta ver se o próprio card é um link ou tem um filho
                    if card.name == 'a' and '/dp/' in card.get('href', ''):
                        link_tag = card
                    else:
                        continue

                href = link_tag.get('href')
                match_id = re.search(r'/dp/([A-Z0-9]{10})', href)
                if not match_id: continue
                prod_id = match_id.group(1)

                if prod_id in links_visitados: continue
                links_visitados.add(prod_id)
                
                full_link = f"https://www.amazon.com.br/dp/{prod_id}"

                # --- 2. Nome ---
                nome = "Oferta Misteriosa"
                img = card.find('img')
                
                # Tenta pegar nome de tags comuns de título
                titulo_tag = card.select_one('div[class*="DealContent-title"], span[class*="a-truncate-full"]')
                if titulo_tag:
                    nome = titulo_tag.get_text(strip=True)
                elif img and img.get('alt'):
                    nome = img.get('alt')
                else:
                    texto = card.get_text(" ", strip=True)
                    if len(texto) > 5: nome = texto[:60] + "..."

                # --- 3. Preço da Oferta ---
                preco = "Ver no site"
                # Procura classes de preço ou o Regex genérico
                price_tag = card.select_one('.a-price .a-offscreen, span[class*="deal-price"]')
                
                if price_tag:
                    preco = price_tag.get_text(strip=True)
                else:
                    # Regex para pegar o primeiro preço que aparecer (R$ XX,XX)
                    texto_full = card.get_text()
                    match_preco = re.search(r'R\$\s?[\d\.,]+', texto_full)
                    if match_preco: preco = match_preco.group(0)

                # --- 4. Porcentagem de Desconto (Opcional) ---
                desconto = ""
                # Procura textos como "20% off", "50% de desconto"
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
            return [{"erro": "Nenhuma oferta direta encontrada.", "titulo": soup.title.string if soup.title else "Sem Título"}]

        return lista_ofertas[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]


