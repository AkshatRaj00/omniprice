from urllib.parse import quote_plus
import httpx
from core.matcher import CrossStoreMatcher

async def search_ajio(query: str, variant: str, client: httpx.AsyncClient) -> dict:
    url = f"https://www.ajio.com/api/search?text={quote_plus(query)}&pageSize=5"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        res = await client.get(url, headers=headers, timeout=8.0)
        if res.status_code == 200:
            products = res.json().get("products", [])
            for item in products:
                brand = item.get("fnlColorVariantData", {}).get("brandName", "")
                name = item.get("name", "")
                title = f"{brand} {name}".strip()
                price_val = item.get("price", {}).get("value")
                img_url = item.get("images", [{}])[0].get("url") if item.get("images") else None

                is_match, score = CrossStoreMatcher.evaluate_match(query, variant, title)
                if is_match and price_val:
                    return {
                        "platform": "Ajio",
                        "title": title,
                        "price": int(price_val),
                        "image_url": img_url,
                        "url": f"https://www.ajio.com{item.get('url', '')}",
                        "match_score": score,
                        "status": "Available"
                    }
    except Exception as e:
        print(f"[AJIO ERROR] {e}")

    return {"platform": "Ajio", "price": None, "image_url": None, "status": "Not Found / Out of Stock"}