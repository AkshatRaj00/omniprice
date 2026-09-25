import re
from typing import Dict
from urllib.parse import urlparse, parse_qs, unquote
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

class BrowserResolver:
    BOGUS_TITLES = {"google search", "google", "online shopping", "flipkart", "amazon"}

    @classmethod
    async def resolve_url_and_metadata(cls, input_url: str) -> Dict[str, str]:
        resolved_url = input_url
        title = ""
        image_url = ""

        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
                res = await client.get(input_url)
                resolved_url = str(res.url)
                html = res.text

                # Case 1: Google Search / Share Links (extract real query from URL params)
                if "google." in resolved_url:
                    parsed_url = urlparse(resolved_url)
                    params = parse_qs(parsed_url.query)
                    if "q" in params:
                        title = unquote(params["q"][0]).replace("+", " ").strip()
                    elif "url" in params:
                        # Redirect inside google link
                        target = unquote(params["url"][0])
                        return await cls.resolve_url_and_metadata(target)

                # Case 2: Flipkart deep client JS redirects (dl.flipkart.com)
                if ("dl.flipkart.com" in resolved_url or len(html) < 3000) and not title:
                    js_redirect = re.search(
                        r'(?:window\.location(?:\.replace|\.href)?\s*=\s*["\']|url=)(https?://(?:www\.)?flipkart\.com/[^"\'>\s]+)',
                        html
                    )
                    if js_redirect:
                        canonical_url = js_redirect.group(1).replace("&amp;", "&")
                        sub_res = await client.get(canonical_url)
                        resolved_url = str(sub_res.url)
                        html = sub_res.text

                # Case 3: Parse real DOM title and image if not already decoded
                if not title:
                    soup = BeautifulSoup(html, "html.parser")
                    
                    og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
                    if og_title and og_title.get("content"):
                        title = og_title["content"].split("|")[0].split(" - ")[0].split(":")[0].strip()

                    if not title or title.lower() in cls.BOGUS_TITLES:
                        h1 = soup.find("h1")
                        if h1:
                            title = h1.get_text(strip=True)
                        elif soup.title:
                            title = soup.title.get_text(strip=True).split("|")[0].split(" - ")[0].strip()

                    og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                    if og_img and og_img.get("content"):
                        image_url = og_img["content"]

                # Case 4: URL Path Slug fallback if title is still bogus or empty
                if not title or title.lower() in cls.BOGUS_TITLES or len(title) < 4:
                    path = urlparse(resolved_url).path
                    slugs = [p for p in path.split("/") if len(p) > 3 and not p.startswith("itm") and p not in ["p", "dl", "s", "search"]]
                    if slugs:
                        title = slugs[0].replace("-", " ")

        except Exception as e:
            print(f"[RESOLVER ERROR] {e}")

        return {
            "resolved_url": resolved_url,
            "title": title or "",
            "image_url": image_url or ""
        }

    @classmethod
    async def close(cls):
        pass