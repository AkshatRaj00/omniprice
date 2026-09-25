import json
import re
import httpx
from bs4 import BeautifulSoup
import logging

log = logging.getLogger("omniprice")

async def extract_myntra_fast(url: str) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0) as client:
        res = await client.get(url)
        if res.status_code != 200:
            return None
            
        html = res.text
        
        # 1. Direct Regex for Myntra Window PdpData
        pdp_match = re.search(r"window\.pdpData\s*=\s*(\{.*?\});?</script>", html)
        if pdp_match:
            try:
                data = json.loads(pdp_match.group(1))
                p_data = data.get("pdpData", {})
                price = p_data.get("price", {}).get("discounted") or p_data.get("price", {}).get("mrp")
                title = p_data.get("name") or p_data.get("title")
                brand = p_data.get("brand", {}).get("name", "")
                if price:
                    return {
                        "store": "Myntra",
                        "title": f"{brand} {title}".strip(),
                        "price": float(price),
                        "currency": "INR",
                        "in_stock": True,
                        "url": str(res.url)
                    }
            except Exception as e:
                log.debug("window.pdpData parse err: %s", e)

        # 2. Schema JSON-LD Fallback
        soup = BeautifulSoup(html, "html.parser")
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                s_data = json.loads(s.string or "{}")
                if s_data.get("@type") == "Product":
                    title = s_data.get("name")
                    offers = s_data.get("offers", {})
                    price = offers.get("price") or (offers[0].get("price") if isinstance(offers, list) else None)
                    if price and "Site Maintenance" not in str(title):
                        return {
                            "store": "Myntra",
                            "title": title,
                            "price": float(price),
                            "currency": "INR",
                            "in_stock": True,
                            "url": str(res.url)
                        }
            except Exception:
                continue

    return None
