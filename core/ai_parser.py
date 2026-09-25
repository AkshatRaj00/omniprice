"""
OmniPrice Autonomous ReAct Intelligence Agent Engine
File: C:\\price_tracker\\price_tracker\\core\\ai_parser.py
Architecture: Multi-Tier Autonomous Agent with Anti-Bot Amazon Bypasser & Live Search Grounding
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import httpx

logger = logging.getLogger("omniprice.agent")
load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()

AGENT_SYSTEM_PROMPT = """You are OmniPrice Autonomous Agent. You operate using a ReAct (Reason-Action-Observation) loop.
Your job is to identify product specifications and extract verified pricing from messy real-world web data.

Given raw metadata, text fragments, or store DOM snippets, you must deduce:
1. brand: Official manufacturer or brand name.
2. model: Exact model name without promotional noise (remove 'Free Shipping', 'Sale', 'Buy Now', etc.).
3. variant: Size, color, volume, storage (or null).
4. price: Final selling price in INR (integer number only).
5. search_query: High-precision 2-4 word search string (Brand + Model) for indexing across other retail platforms.

STRICT JSON ONLY (No markdown formatting, no explanations):
{"brand": "string", "model": "string", "variant": "string or null", "price": integer, "search_query": "string"}"""

class AutonomousAgentToolkit:
    @staticmethod
    async def tool_fetch_url(url: str) -> str:
        # Realistic desktop browser footprint to bypass Amazon / Flipkart bot-walls
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        try:
            async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(url)
                return resp.text if resp.status_code == 200 else ""
        except Exception as e:
            logger.warning("[AGENT TOOL] Fetch failed: %s", e)
            return ""

    @staticmethod
    async def tool_search_live_fallback(query: str) -> Optional[int]:
        """Tool: When a bot-wall blocks the direct page, search live retail index for true price."""
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query + ' price India amazon flipkart')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            async with httpx.AsyncClient(headers=headers, timeout=8.0, follow_redirects=True) as client:
                res = await client.get(search_url)
                if res.status_code == 200:
                    matches = re.findall(r"(?:₹|rs\.?|inr)\s*([0-9,]+)", res.text, re.IGNORECASE)
                    for m in matches:
                        clean = int(re.sub(r"[^\d]", "", m))
                        if 99 < clean < 5_000_000:
                            return clean
        except Exception:
            pass
        return None

    @staticmethod
    def tool_inspect_dom(html: str) -> Dict[str, Any]:
        out = {"title": None, "image": None, "price_candidates": [], "cleaned_text": ""}
        if not html:
            return out

        soup = BeautifulSoup(html, "html.parser")

        # OpenGraph
        for prop in ["og:title", "twitter:title"]:
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                out["title"] = tag["content"].strip()
                break

        for prop in ["og:image", "twitter:image"]:
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                out["image"] = tag["content"].strip()
                break

        if not out["title"] and soup.find("title"):
            out["title"] = soup.title.get_text(strip=True).split("|")[0].split("-")[0].strip()

        # Amazon specific price classes
        for az_cls in ["a-price-whole", "a-offscreen", "priceToPay"]:
            for elem in soup.find_all(class_=az_cls):
                num = re.sub(r"[^\d]", "", elem.get_text().split(".")[0])
                if num and num.isdigit() and int(num) > 0:
                    out["price_candidates"].append(int(num))

        # Flipkart/General classes
        for cls_name in ["Nx9bqj", "Nx9bqj CxhGGd", "_30jeq3", "prod-sp", "pdp-price"]:
            for elem in soup.find_all(class_=cls_name):
                num = re.sub(r"[^\d]", "", elem.get_text().split(".")[0])
                if num and num.isdigit() and int(num) > 0:
                    out["price_candidates"].append(int(num))

        # Schema JSON-LD
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and "offers" in item:
                        offers = item["offers"]
                        offers_list = offers if isinstance(offers, list) else [offers]
                        for off in offers_list:
                            if isinstance(off, dict) and "price" in off:
                                raw_p = re.sub(r"[^\d]", "", str(off.get("price", "")))
                                if raw_p and raw_p.isdigit():
                                    p = int(raw_p)
                                    if p > 0:
                                        out["price_candidates"].append(p)
            except Exception:
                continue

        # In-page raw INR text
        raw_matches = re.findall(r"(?:₹|rs\.?|inr)\s*([0-9,]+)", html[:60000], re.IGNORECASE)
        for m in raw_matches:
            digits_only = re.sub(r"[^\d]", "", m)
            if digits_only and digits_only.isdigit():
                val = int(digits_only)
                if 30 < val < 15_000_000:
                    out["price_candidates"].append(val)

        for tag in soup(["script", "style", "noscript", "svg", "header", "footer"]):
            tag.decompose()
        out["cleaned_text"] = " ".join(soup.stripped_strings)[:2500]

        return out

class AutonomousAgentCore:
    def __init__(self):
        self.toolkit = AutonomousAgentToolkit()

    async def _reason_with_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        # Tier 1: Groq qwen/qwen3.8-27b
        if GROQ_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    res = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": "qwen/qwen3.8-27b",
                            "messages": [
                                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"}
                        }
                    )
                    if res.status_code == 200:
                        return json.loads(res.json()["choices"][0]["message"]["content"])
            except Exception as e:
                logger.warning("[AGENT] Groq reasoning failed: %s", e)

        # Tier 2: OpenRouter Free
        if OPENROUTER_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "OmniPrice"
                        },
                        json={
                            "model": "openrouter/free",
                            "messages": [
                                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.1
                        }
                    )
                    if res.status_code == 200:
                        raw = res.json()["choices"][0]["message"]["content"]
                        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
                        return json.loads(clean)
            except Exception as e:
                logger.warning("[AGENT] OpenRouter free router failed: %s", e)

        return None

    async def run(self, raw_input: str) -> Dict[str, Any]:
        html = ""
        is_url = raw_input.strip().startswith(("http://", "https://"))
        
        if is_url:
            html = await self.toolkit.tool_fetch_url(raw_input)
            dom_data = self.toolkit.tool_inspect_dom(html)
        else:
            dom_data = self.toolkit.tool_inspect_dom(raw_input)

        candidates = dom_data.get("price_candidates", [])
        title = dom_data.get("title") or ""
        
        # If title empty, derive from URL slug (e.g., layasa-Green-Sneakers-for-Men)
        if not title and is_url:
            parsed = urlparse(raw_input)
            slug = [seg for seg in parsed.path.split("/") if seg and seg not in ("dp", "p", "product")]
            if slug:
                title = slug[0].replace("-", " ").title()

        title = title or "Retail Product"

        context_prompt = f"""Observe this product data and extract exact entity details:
URL or Input: {raw_input[:300]}
Detected Page Title: {title}
Candidate Prices Found: {candidates[:8]}
Page Excerpt: {dom_data.get('cleaned_text', '')[:1400]}"""

        decision = await self._reason_with_llm(context_prompt)

        final_brand = decision.get("brand") if decision else None
        final_model = decision.get("model") if decision else None
        final_price = decision.get("price") if decision else None
        final_query = decision.get("search_query") if decision else None

        if not final_brand or not final_model:
            stopwords = {"buy", "online", "price", "india", "discount", "free", "men", "women", "sneakers", "shoes"}
            tokens = [w for w in re.sub(r"[^\w\s]", "", title).split() if w.lower() not in stopwords]
            final_brand = tokens[0] if tokens else "Generic"
            final_model = " ".join(tokens[1:4]) if len(tokens) > 1 else title[:25]
            final_query = f"{final_brand} {final_model}".strip()

        # Deterministic Price Extraction Chain
        if not final_price or not str(final_price).isdigit() or int(final_price) <= 0:
            if candidates:
                final_price = candidates[0]
            else:
                # Anti-bot trigger: scrape search index for live price
                logger.info("[AGENT REASONING] Target page price blocked. Calling tool_search_live_fallback...")
                fallback_p = await self.toolkit.tool_search_live_fallback(f"{final_brand} {final_model}")
                final_price = fallback_p or 499

        return {
            "brand": final_brand,
            "model": final_model,
            "variant": decision.get("variant", "STANDARD") if decision else "STANDARD",
            "price": int(final_price),
            "currency": "INR",
            "search_query": final_query or f"{final_brand} {final_model}",
            "image_url": dom_data.get("image")
        }

agent_core = AutonomousAgentCore()

async def extract_product_with_llm(raw_context: str) -> Dict[str, Any]:
    return await agent_core.run(raw_context)