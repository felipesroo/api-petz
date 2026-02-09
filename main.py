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
    return {"status": "Robô Amazon Universal Online 🌎"}

@app.get("/scrape")
def rodar_robo():
    # DICA: Tente mudar essa URL para uma categoria específica para ver mais produtos!
    # Ex: https://www.amazon.com.br/gp/bestsellers/books/
    url_alvo = "https://www.amazon.com.br/gp/bestsellers/?ref_=nav_cs_bestsellers"
    
    print(f"Iniciando raspagem em: {url_alvo}")
    
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'country_code': 'br',
        'device_type': 'mobile', # Mobile costuma ser mais leve
    }

    try:
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
        
        if r.status_code != 200:
            return [{"erro": f"Erro API: {r.status_code}", "msg": r.text}]

        soup = BeautifulSoup(r.text, 'html.parser')
        lista_produtos = []
        
        # ESTRATÉGIA UNIVERSAL (Varrer Links)
        # Em vez de procurar divs específicas, procuramos QUALQUER link de produto
        # O padrão da Amazon é amazon.com.br/.../dp/CÓDIGO
        links_produtos = soup.select('a[href*="/dp/"]')
        
        print(f"Links brutos encontrados: {len(links_produtos)}")
        
        links_visitados = set()

        for link in links_produtos:
            try:
                href = link.get('href')
                
                # Limpeza do Link (Pega só até o código do produto para evitar duplicatas)
                if not href: continue
                match_id = re.search(r'/dp/([A-Z0-9]{10})', href)
                if not match_id: continue
                prod_id = match_id.group(1)
                
                if prod_id in links_visitados: continue
                links_visitados.add(prod_id)
                
                full_link = f"https://www.amazon.com.br/dp/{prod_id}"

                # Tenta achar o Nome e Preço subindo na árvore do HTML
                # (Procura no elemento pai do link)
                card = link.find_parent('div', class_=lambda x: x and 'zg' in x) # Tenta achar o card pai
                if not card:
                    card = link.find_parent('li') # Tenta achar item de lista
                if not card:
                    card = link.find_parent('div') # Pega o div mais próximo

                if not card: continue

                # Extração de Nome
                nome = "Nome não detectado"
                img = card.find('img')
                if img and img.get('alt'):
                    nome = img.get('alt')
                else:
                    # Tenta pegar texto do próprio link ou vizinhos
                    texto_card = card.get_text(" ", strip=True)
                    if len(texto_card) > 5:
                         # Pega os primeiros 50 caracteres como nome provisório se não tiver imagem
                         nome = texto_card[:50] + "..."

                # Extração de Preço
                preco = "Ver no site"
                # Procura padrão de preço (R$ XX,XX) no texto do cartão inteiro
                texto_completo = card.get_text()
                match_preco = re.search(r'R\$\s?(\d+[\.,]\d{2})', texto_completo)
                if match_preco:
                    preco = match_preco.group(0)

                # Extração de Imagem
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
            return [{"erro": "Nenhum produto encontrado. Tente uma URL de categoria específica.", "titulo": soup.title.string}]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]

