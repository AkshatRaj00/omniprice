import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from core.matcher import CrossStoreMatcher

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"'
}

async def search_amazon(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    queries_to_try = [query]
    tokens = query.split()
    if len(tokens) > 2:
        queries_to_try.append(f"{tokens[0]} {tokens[1]}")

    for search_term in queries_to_try:
        url = f"https://www.amazon.in/s?k={quote_plus(search_term)}"
        try:
            res = await client.get(url, headers=HEADERS, timeout=8.0)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                results = soup.select("div[data-component-type='s-search-result']")
                for item in results:
                    t_node = item.h2
                    p_node = item.select_one(".a-price-whole")
                    l_node = item.select_one("h2 a")
                    img_node = item.select_one("img.s-image")
                    
                    if t_node and p_node and l_node:
                        title = t_node.get_text(strip=True)
                        price = int(re.sub(r"[^\d]", "", p_node.get_text(strip=True)))
                        img_url = img_node.get("src") if img_node else None
                        
                        is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                        if is_match:
                            return {
                                "platform": "Amazon",
                                "title": title,
                                "price": price,
                                "image_url": img_url,
                                "url": "https://www.amazon.in" + l_node.get("href", "").split("?")[0],
                                "match_score": score,
                                "status": "Available"
                            }
        except Exception:
            pass

    return {"platform": "Amazon", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}