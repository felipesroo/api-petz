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
    return {"status": "Robô Amazon Multi-Categorias Online 📦"}

@app.get("/scrape")
def rodar_robo():
    # --- LISTA DE LINKS PARA RASPAR ---
    CATEGORIAS = [
        "https://www.amazon.com.br/s?i=computers&rh=n%3A16364755011%2Cp_72%3A4-&s=popularity-rank&content-id=amzn1.sym.ad70a180-419e-40e7-9bae-dd34c8922b7b&pd_rd_r=4ea0e4ad-4ff1-45ae-beda-20260872975a&pd_rd_w=SHRt0&pd_rd_wg=WzbrP&pf_rd_p=ad70a180-419e-40e7-9bae-dd34c8922b7b&pf_rd_r=0Y8PDZYZA5EJ0D2YF2WJ&ref=Oct_d_otopr_S",
        "https://www.amazon.com.br/gp/bestsellers/appliances/16745370011/ref=zg_bs_nav_appliances_1_19821156011?pd_rd_w=7NcPJ&content-id=amzn1.sym.6e5fc16c-daad-49dd-8714-5bfa615f44d2&pf_rd_p=6e5fc16c-daad-49dd-8714-5bfa615f44d2&pf_rd_r=D540HPJETP0YQZ913X7X&pd_rd_wg=vOWj8&pd_rd_r=863d6d19-90ee-4971-aa78-8220140eb6de",
        "https://www.amazon.com.br/gp/bestsellers/kitchen/17125504011/ref=zg_bs_nav_kitchen_2_17124722011?pd_rd_w=jpdAP&content-id=amzn1.sym.3e2d870b-28dd-4f6f-8589-8d77d8626986&pf_rd_p=3e2d870b-28dd-4f6f-8589-8d77d8626986&pf_rd_r=D540HPJETP0YQZ913X7X&pd_rd_wg=vOWj8&pd_rd_r=863d6d19-90ee-4971-aa78-8220140eb6de"
    ]
    # ----------------------------------
    
    lista_global_produtos = []
    erros = []

    print(f"Iniciando raspagem de {len(CATEGORIAS)} categorias...")

    # LOOP: Repete o processo para cada URL da lista
    for url_alvo in CATEGORIAS:
        print(f"Raspando: {url_alvo}")
        
        payload = {
            'api_key': API_KEY, 
            'url': url_alvo, 
            'country_code': 'br',
            'device_type': 'mobile', 
            'premium': 'true', 
            'render': 'false'
        }

        try:
            # Tenta raspar a URL atual
            r = requests.get('http://api.scraperapi.com', params=payload, timeout=90)
            
            if r.status_code != 200:
                print(f"Erro na URL {url_alvo}: {r.status_code}")
                erros.append(f"Erro {r.status_code} em {url_alvo}")
                continue # Pula para a próxima categoria sem quebrar

            soup = BeautifulSoup(r.text, 'html.parser')
            
            # --- EXTRAÇÃO (A mesma lógica blindada de antes) ---
            links_produtos = soup.select('a[href*="/dp/"]')
            links_visitados = set()

            cont_categoria = 0

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

                    card = link.find_parent('div', class_=lambda x: x and 'zg' in x) 
                    if not card: card = link.find_parent('li')
                    if not card: card = link.find_parent('div')

                    if not card: continue

                    # Nome
                    nome = "Nome não detectado"
                    img = card.find('img')
                    if img and img.get('alt'):
                        nome = img.get('alt')
                    else:
                        texto = card.get_text(" ", strip=True)
                        if len(texto) > 5: nome = texto[:80] + "..."

                    # Preço (Correção do Ponto)
                    preco = "Ver no site"
                    price_tag = card.select_one('.a-offscreen, span.p13n-sc-price')
                    if price_tag:
                        preco = price_tag.get_text(strip=True)
                    else:
                        texto_full = card.get_text()
                        match_preco = re.search(r'R\$\s?[\d\.,]+', texto_full)
                        if match_preco: preco = match_preco.group(0)

                    imagem = img.get('src') if img else ""

                    lista_global_produtos.append({
                        "nome": nome,
                        "preco": preco,
                        "link": full_link,
                        "imagem": imagem,
                        "categoria_origem": url_alvo # Dica: Adicionei isso pra você saber de onde veio
                    })
                    cont_categoria += 1
                except:
                    continue
            
            print(f"Sucesso: {cont_categoria} produtos encontrados nesta categoria.")

        except Exception as e:
            print(f"Erro fatal na URL {url_alvo}: {str(e)}")
            erros.append(f"Erro de script em {url_alvo}")
    
    # RESULTADO FINAL
    if not lista_global_produtos:
        return [{"erro": "Nenhum produto encontrado em nenhuma lista.", "detalhes": erros}]

    return lista_global_produtos
