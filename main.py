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
    return {"status": "Robô Amazon Preço Correto Online 💲"}

@app.get("/scrape")
def rodar_robo():
    # URL da categoria Cozinha (mas funciona para qualquer uma)
    url_alvo = "https://www.amazon.com.br/s?i=computers&rh=n%3A16364755011%2Cp_72%3A4-&s=popularity-rank&content-id=amzn1.sym.ad70a180-419e-40e7-9bae-dd34c8922b7b&pd_rd_r=4ea0e4ad-4ff1-45ae-beda-20260872975a&pd_rd_w=SHRt0&pd_rd_wg=WzbrP&pf_rd_p=ad70a180-419e-40e7-9bae-dd34c8922b7b&pf_rd_r=0Y8PDZYZA5EJ0D2YF2WJ&ref=Oct_d_otopr_S"
    
    print(f"Iniciando raspagem em: {url_alvo}")
    
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
        lista_produtos = []
        
        # Seleciona links de produtos (/dp/)
        links_produtos = soup.select('a[href*="/dp/"]')
        print(f"Links encontrados: {len(links_produtos)}")
        
        links_visitados = set()

        for link in links_produtos:
            try:
                href = link.get('href')
                if not href: continue
                
                match_id = re.search(r'/dp/([A-Z0-9]{10})', href)
                if not match_id: continue
                prod_id = match_id.group(1)
                
                if prod_id in links_visitados: continue
                links_visitados.add(prod_id)
                
                full_link = f"https://www.amazon.com.br/dp/{prod_id}"

                # Sobe para o card pai
                card = link.find_parent('div', class_=lambda x: x and 'zg' in x) 
                if not card: card = link.find_parent('li')
                if not card: card = link.find_parent('div')

                if not card: continue

                # --- EXTRAÇÃO DE NOME ---
                nome = "Nome não detectado"
                img = card.find('img')
                if img and img.get('alt'):
                    nome = img.get('alt')
                else:
                    texto = card.get_text(" ", strip=True)
                    if len(texto) > 5: nome = texto[:80] + "..."

                # --- EXTRAÇÃO DE PREÇO CORRIGIDA ---
                preco = "Ver no site"
                
                # TENTATIVA 1: Buscar classes específicas da Amazon (O jeito mais seguro)
                # .a-offscreen = Texto escondido para acessibilidade (Ex: R$ 3.299,00)
                price_tag = card.select_one('.a-offscreen, span.p13n-sc-price, span._cDEzb_p13n-sc-price_3mJ9Z')
                
                if price_tag:
                    preco = price_tag.get_text(strip=True)
                else:
                    # TENTATIVA 2: Regex melhorado para Moeda Brasileira
                    # Procura R$ seguido de números, pontos e vírgulas
                    texto_full = card.get_text()
                    match_preco = re.search(r'R\$\s?[\d\.,]+', texto_full)
                    if match_preco:
                        preco = match_preco.group(0)

                # --- EXTRAÇÃO DE IMAGEM ---
                imagem = img.get('src') if img else ""

                lista_produtos.append({
                    "nome": nome,
                    "preco": preco,
                    "link": full_link,
                    "imagem": imagem
                })

            except:
                continue

        if not lista_produtos:
            return [{"erro": "Nenhum produto encontrado.", "titulo": soup.title.string if soup.title else "Sem título"}]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
