import re
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

async def fetch_flipkart_product(url: str, client: httpx.AsyncClient) -> dict:
    try:
        res = await client.get(url, headers=HEADERS, timeout=10.0)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            
            title = ""
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
            
            price = None
            price_el = soup.select_one("div._30jeq3, div.Nx9bqj, div._16Jk6d, div.CxhGGd")
            if price_el:
                price = int(re.sub(r"[^\d]", "", price_el.get_text(strip=True)))

            img_url = ""
            img_el = soup.select_one("img._396cs4, img._2r_T1I, img.DByuf4")
            if img_el and img_el.get("src"):
                img_url = img_el["src"]

            if price:
                return {
                    "platform": "Flipkart",
                    "title": title or "Flipkart Verified Product",
                    "price": price,
                    "image_url": img_url,
                    "url": url,
                    "status": "Available"
                }
    except Exception as e:
        print(f"[FLIPKART ERROR] {e}")

    return {
        "platform": "Flipkart",
        "title": None,
        "price": None,
        "image_url": None,
        "url": url,
        "status": "Out of Stock"
    }