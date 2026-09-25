from urllib.parse import quote_plus
import httpx
from core.matcher import CrossStoreMatcher

async def search_myntra(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.myntra.com/gateway/v2/search/{quote_plus(query)}?p=1&rows=5"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-meta-app": "channel=web",
        "Accept": "application/json"
    }
    try:
        res = await client.get(url, headers=headers, timeout=8.0)
        if res.status_code == 200:
            products = res.json().get("products", [])
            for item in products:
                brand = item.get("brand", "")
                info = item.get("additionalInfo", "") or item.get("productName", "")
                title = f"{brand} {info}".strip()
                price = item.get("price")
                img_url = item.get("searchImage")

                is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                if is_match and price:
                    return {
                        "platform": "Myntra",
                        "title": title,
                        "price": int(price),
                        "image_url": img_url,
                        "url": f"https://www.myntra.com/{item.get('landingPageUrl')}",
                        "match_score": score,
                        "status": "Available"
                    }
    except Exception as e:
        print(f"[MYNTRA ERROR] {e}")

    return {"platform": "Myntra", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}