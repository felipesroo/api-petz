import os
import re
import json
import time
import csv
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.petz.com.br/colecao/UT-outlet-petz"
OUT_JSON = os.getenv("OUT_JSON", "petz_outlet.json")
OUT_CSV = os.getenv("OUT_CSV", "petz_outlet.csv")
SLEEP_SEC = float(os.getenv("SLEEP_SEC", "1.2"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "50"))  # limite de segurança

HEADERS = {
    "User-Agent": os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(HEADERS)
session.timeout = 25


def normalize_price(text: str):
    if not text:
        return None
    t = text.strip()
    # pega algo tipo "R$ 19,90" / "19,90"
    m = re.search(r"(\d{1,3}(\.\d{3})*,\d{2})", t)
    if not m:
        return None
    val = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(val)
    except:
        return None


def extract_from_html(html: str, page_url: str):
    soup = BeautifulSoup(html, "lxml")

    products = []

    # Estratégia 1: procurar links de produto e tentar subir pro card
    # (seletores podem variar; por isso tentamos múltiplos padrões)
    candidate_links = soup.select('a[href*="/produto/"], a[href*="/produtos/"], a[href*="/p/"]')

    seen = set()
    for a in candidate_links:
        href = a.get("href")
        if not href:
            continue
        full_link = urljoin(page_url, href)
        if full_link in seen:
            continue
        seen.add(full_link)

        # tenta achar um "card" acima do link
        card = a
        for _ in range(6):
            if card and getattr(card, "name", None) in ("article", "li", "div"):
                cls = " ".join(card.get("class", [])).lower()
                if any(k in cls for k in ["product", "produto", "card", "shelf", "item"]):
                    break
            card = card.parent

        title = None
        price = None
        old_price = None
        image = None

        # título
        if a.get_text(strip=True):
            title = a.get_text(" ", strip=True)

        if card:
            # imagem
            img = card.select_one("img")
            if img:
                image = img.get("src") or img.get("data-src") or img.get("data-lazy") or img.get("srcset")
                if image and " " in image and "http" in image:
                    # se for srcset, pega o primeiro
                    image = image.split()[0]

            # preços (pega vários textos e tenta extrair números)
            text = card.get_text(" ", strip=True)
            # tenta achar 2 preços (promo e original)
            found = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", text)
            if found:
                # heurística: o menor costuma ser o atual, maior o antigo
                nums = []
                for f in found:
                    try:
                        nums.append(float(f.replace(".", "").replace(",", ".")))
                    except:
                        pass
                if nums:
                    nums_sorted = sorted(set(nums))
                    price = nums_sorted[0]
                    if len(nums_sorted) > 1:
                        old_price = nums_sorted[-1]

        if not title:
            continue

        products.append({
            "title": title,
            "price": price,
            "old_price": old_price,
            "link": full_link,
            "image": image,
            "source": page_url,
        })

    # remove “falsos positivos” (links que não parecem produto)
    cleaned = []
    for p in products:
        # exige alguma indicação de preço OU imagem OU caminho típico
        if (p["price"] is not None) or (p["image"]) or ("/produto" in p["link"] or "/p/" in p["link"]):
            cleaned.append(p)

    # dedupe por link
    uniq = {}
    for p in cleaned:
        uniq[p["link"]] = p
    return list(uniq.values())


def guess_next_page_url(current_url: str, html: str):
    soup = BeautifulSoup(html, "lxml")

    # tenta achar botão "próximo"
    for sel in [
        'a[rel="next"]',
        'a[aria-label*="Próxima"]',
        'a[aria-label*="próxima"]',
        'a:contains("Próxima")',
        'a:contains("proxima")',
    ]:
        try:
            a = soup.select_one(sel)
        except Exception:
            a = None
        if a and a.get("href"):
            return urljoin(current_url, a["href"])

    # fallback: tenta usar padrão ?page=
    parsed = urlparse(current_url)
    qs = parse_qs(parsed.query)
    page = int(qs.get("page", ["1"])[0]) if "page" in qs else 1
    next_page = page + 1

    if "
