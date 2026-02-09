import os
import re
import json
import time
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

BASE_URL = "https://www.petz.com.br/colecao/UT-outlet-petz"

SCRAPERAPI_KEY = os.getenv("cf26a5bf4dba51e058af2258d6eb4b4f")  # vai no EasyPanel
SCRAPERAPI_ENDPOINT = "https://api.scraperapi.com"

OUT_JSON = os.getenv("OUT_JSON", "/data/petz_outlet.json")
OUT_CSV  = os.getenv("OUT_CSV",  "/data/petz_outlet.csv")
SLEEP_SEC = float(os.getenv("SLEEP_SEC", "1.0"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "30"))

SCRAPER_COUNTRY = os.getenv("SCRAPER_COUNTRY", "br")
SCRAPER_PREMIUM = os.getenv("SCRAPER_PREMIUM", "true").lower() == "true"
SCRAPER_RENDER  = os.getenv("SCRAPER_RENDER", "false").lower() == "true"


def fetch_html_with_scraperapi(target_url: str) -> str:
    if not SCRAPERAPI_KEY:
        raise RuntimeError("Você precisa definir a env SCRAPERAPI_KEY no EasyPanel.")

    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": target_url,
        "country_code": SCRAPER_COUNTRY,
        "premium": str(SCRAPER_PREMIUM).lower(),
        "render": str(SCRAPER_RENDER).lower(),
    }

    r = requests.get(SCRAPERAPI_ENDPOINT, params=params, timeout=90)
    r.raise_for_status()
    return r.text


def extract_products(html: str, page_url: str):
    soup = BeautifulSoup(html, "lxml")

    # tentativa genérica: achar links que pareçam produto
    candidate_links = soup.select('a[href*="/produto/"], a[href*="/produtos/"], a[href*="/p/"]')

    products = {}
    for a in candidate_links:
        href =
