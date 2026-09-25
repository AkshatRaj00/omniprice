import re
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
from core.matcher import CrossStoreMatcher

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

# 1. Nykaa
async def search_nykaa(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.nykaa.com/search/result/?q={quote_plus(query)}"
    try:
        res = await client.get(url, headers=HEADERS, timeout=8.0)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for card in soup.select("div.productWrapper"):
                t = card.select_one("div.css-xrzmfa")
                p = card.select_one("span.css-111z9ua")
                l = card.select_one("a.css-qlopj5")
                img = card.select_one("img.css-11gn9r6")
                if t and p and l:
                    title = t.get_text(strip=True)
                    price = int(re.sub(r"[^\d]", "", p.get_text(strip=True)))
                    img_url = img.get("src") if img else None
                    is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                    if is_match:
                        return {"platform": "Nykaa", "title": title, "price": price, "image_url": img_url, "url": "https://www.nykaa.com" + l.get("href", ""), "status": "Available"}
    except Exception:
        pass
    return {"platform": "Nykaa", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}

# 2. Tata CLiQ
async def search_tatacliq(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.tatacliq.com/marketapis/tcxtarget/searchProduct?searchText={quote_plus(query)}&page=0&pageSize=5"
    try:
        res = await client.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=8.0)
        if res.status_code == 200:
            items = res.json().get("searchresult", [])
            for item in items:
                title = item.get("productname", "")
                price = item.get("price", {}).get("price")
                img_url = item.get("imageURL")
                is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                if is_match and price:
                    return {"platform": "Tata CLiQ", "title": title, "price": int(float(price)), "image_url": img_url, "url": f"https://www.tatacliq.com{item.get('webURL', '')}", "status": "Available"}
    except Exception:
        pass
    return {"platform": "Tata CLiQ", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}

# 3. Snapdeal
async def search_snapdeal(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.snapdeal.com/search?keyword={quote_plus(query)}"
    try:
        res = await client.get(url, headers=HEADERS, timeout=8.0)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for item in soup.select("div.product-tuple-listing"):
                t = item.select_one("p.product-title")
                p = item.select_one("span.product-price")
                l = item.select_one("a.dp-widget-link")
                img = item.select_one("picture.picture-elem source, img.product-image")
                if t and p and l:
                    title = t.get_text(strip=True)
                    price = int(re.sub(r"[^\d]", "", p.get_text(strip=True)))
                    img_url = img.get("srcset") or img.get("src") if img else None
                    is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                    if is_match:
                        return {"platform": "Snapdeal", "title": title, "price": price, "image_url": img_url, "url": l.get("href", ""), "status": "Available"}
    except Exception:
        pass
    return {"platform": "Snapdeal", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}

# 4. Purplle
async def search_purplle(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.purplle.com/search?q={quote_plus(query)}"
    try:
        res = await client.get(url, headers=HEADERS, timeout=8.0)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for card in soup.select("div.p-card"):
                t = card.select_one("span.p-title")
                p = card.select_one("span.p-price")
                l = card.select_one("a")
                img = card.select_one("img")
                if t and p and l:
                    title = t.get_text(strip=True)
                    price = int(re.sub(r"[^\d]", "", p.get_text(strip=True)))
                    img_url = img.get("src") if img else None
                    is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                    if is_match:
                        return {"platform": "Purplle", "title": title, "price": price, "image_url": img_url, "url": "https://www.purplle.com" + l.get("href", ""), "status": "Available"}
    except Exception:
        pass
    return {"platform": "Purplle", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}

# 5. JioMart
async def search_jiomart(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.jiomart.com/catalogsearch/result?q={quote_plus(query)}"
    try:
        res = await client.get(url, headers=HEADERS, timeout=8.0)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for item in soup.select("div.ais-InfiniteHits-item, div.product-card"):
                t = item.select_one("div.line-clamp-2, h3.title")
                p = item.select_one("span.jm-heading-xxs, span.final-price")
                l = item.select_one("a")
                img = item.select_one("img")
                if t and p and l:
                    title = t.get_text(strip=True)
                    price = int(re.sub(r"[^\d]", "", p.get_text(strip=True)))
                    img_url = img.get("src") if img else None
                    is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                    if is_match:
                        return {"platform": "JioMart", "title": title, "price": price, "image_url": img_url, "url": "https://www.jiomart.com" + l.get("href", ""), "status": "Available"}
    except Exception:
        pass
    return {"platform": "JioMart", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}

# 6. Tira Beauty
async def search_tira(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.trbc.io/api/v1/search?query={quote_plus(query)}&page=1&size=5"
    try:
        res = await client.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=8.0)
        if res.status_code == 200:
            items = res.json().get("items", [])
            for item in items:
                title = item.get("name", "")
                price = item.get("price", {}).get("effective")
                img_url = item.get("media", [{}])[0].get("url") if item.get("media") else None
                is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                if is_match and price:
                    return {"platform": "Tira Beauty", "title": title, "price": int(price), "image_url": img_url, "url": f"https://www.tirabeauty.com/product/{item.get('slug')}", "status": "Available"}
    except Exception:
        pass
    return {"platform": "Tira Beauty", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}