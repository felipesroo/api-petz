from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import json

app = FastAPI()

# --- COLOQUE SUA CHAVE AQUI ---
API_KEY = "cf26a5bf4dba51e058af2258d6eb4b4f"
# ------------------------------

@app.get("/")
def home():
    return {"status": "Robô Petz via API Online 🚀"}

@app.get("/scrape")
def rodar_robo():
    print("Iniciando raspagem via ScraperAPI...")
    
    # URL que queremos raspar
    url_alvo = "https://www.petz.com.br/cachorro/racao/racao-seca"
    
    # Monta o pedido para o ScraperAPI
    # render=true avisa que o site usa Javascript (importante para Petz)
    payload = {
        'api_key': API_KEY, 
        'url': url_alvo, 
        'render': 'true',
        'country_code': 'br' # Usa IP do Brasil
    }

    try:
        # Faz o pedido (quem acessa a Petz é o ScraperAPI, não sua VPS)
        r = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
        
        if r.status_code != 200:
            return [{"erro": f"Falha na API: {r.status_code}", "detalhe": r.text}]

        # O ScraperAPI devolve o HTML prontinho
        soup = BeautifulSoup(r.text, 'html.parser')
        
        lista_produtos = []
        
        # Procura os cards (mesma lógica visual ou link)
        # Tenta pegar todos os links de produtos
        links = soup.select('a[href*="/produto/"]')
        
        links_visitados = set()

        for link_tag in links:
            try:
                href = link_tag.get('href')
                if not href: continue
                
                full_link = "https://www.petz.com.br" + href if not href.startswith('http') else href
                
                if full_link in links_visitados:
                    continue
                links_visitados.add(full_link)

                # Pega o texto do link ou do pai
                texto = link_tag.get_text(" ", strip=True)
                if len(texto) < 5:
                    parent = link_tag.find_parent()
                    if parent:
                        texto = parent.get_text(" ", strip=True)

                # Busca Preço (Simples procura por R$)
                preco = "0"
                if "R$" in texto:
                    # Tenta limpar string para achar o preço
                    partes = texto.split('R$')
                    if len(partes) > 1:
                        # Pega os primeiros caracteres depois do R$
                        preco_sujo = partes[1].strip().split(' ')[0]
                        preco = preco_sujo.replace(',', '.')

                # Busca Imagem
                img_tag = link_tag.find('img')
                imagem = img_tag.get('src') if img_tag else ""

                # Filtro básico de qualidade
                if len(texto) > 10 and "R$" in texto:
                    # Limpa o nome (tira o preço do nome)
                    nome = texto.split('R$')[0].strip()
                    
                    lista_produtos.append({
                        "nome": nome,
                        "preco": preco,
                        "link": full_link,
                        "imagem": imagem
                    })

            except:
                continue
        
        if not lista_produtos:
            return [{"erro": "Nenhum produto encontrado", "html_sample": str(soup)[:200]}]

        return lista_produtos[:50]

    except Exception as e:
        return [{"erro": f"Erro interno: {str(e)}"}]
