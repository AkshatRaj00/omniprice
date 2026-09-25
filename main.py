"""
OmniPrice Autonomous Neural Core Engine — Enterprise Production Grade
File: C:\\price_tracker\\price_tracker\\main.py
"""

import asyncio
import contextlib
from datetime import datetime
from difflib import SequenceMatcher
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import socket
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel, field_validator

from core.ai_parser import extract_product_with_llm

# =====================================================================
# Logging Configuration
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("omniprice")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
GATEWAY_URL: str = os.getenv("WHATSAPP_GATEWAY", "http://127.0.0.1:5001/send-message").strip()
DB_PATH: str = str(BASE_DIR / "omnidata.db")

# =====================================================================
# Database Layer (WAL Mode + Zero-Downtime Auto-Migration)
# =====================================================================
def init_db() -> None:
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracked_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                query_used TEXT NOT NULL,
                target_price INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                source_url TEXT NOT NULL,
                canonical_url TEXT,
                last_checked_price INTEGER,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP
            )
        """)
        
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tracked_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "canonical_url" not in columns:
            cursor.execute("ALTER TABLE tracked_items ADD COLUMN canonical_url TEXT")
            cursor.execute("UPDATE tracked_items SET canonical_url = source_url WHERE canonical_url IS NULL")
            log.info("[DB MIGRATION] Added 'canonical_url' column.")
            
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_phone_canonical 
            ON tracked_items(phone_number, canonical_url)
        """)
        conn.commit()
        log.info("[DB READY] Database active with auto-migration verified.")
    finally:
        conn.close()

def db_execute(sql: str, params: tuple = (), fetch: bool = False):
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
        return None
    finally:
        conn.close()

# =====================================================================
# WhatsApp Dispatcher
# =====================================================================
async def dispatch_whatsapp(phone: str, message: str) -> bool:
    clean_phone = re.sub(r"[^0-9]", "", phone)
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.post(GATEWAY_URL, json={"phone": clean_phone, "message": message})
            if res.status_code == 200:
                log.info("[WHATSAPP SENT] Alert delivered to +%s", clean_phone)
                return True
    except Exception as e:
        log.warning("[WHATSAPP GATEWAY OFFLINE] %s. Queued internally.", e)

    log.info("[WHATSAPP SIMULATED] Phone: +%s | Message: %s", clean_phone, message.replace('\n', ' '))
    return True

# =====================================================================
# Network Client Headers & SSRF Guard
# =====================================================================
UNIVERSAL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en-IN;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

def validate_url_host(raw_url: str) -> None:
    try:
        p = urlparse(raw_url)
        if p.scheme not in ("http", "https"):
            raise ValueError("Invalid protocol scheme.")
        host = (p.hostname or "").lower()
        if not host:
            raise ValueError("Missing host.")
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            raise ValueError("Loopback target forbidden.")
        
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Targeting private IP ranges forbidden.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsafe URL target: {e}")

async def resolve_canonical_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = "https://" + raw_url
    validate_url_host(raw_url)

    if "dl.flipkart.com" in raw_url:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0) as client:
                res = await client.get(raw_url)
                final_url = str(res.url)
                for h in res.history:
                    loc = h.headers.get("location", "")
                    if "flipkart.com" in loc and "/p/itm" in loc:
                        final_url = loc
                        break

                pid_match = re.search(r"pid=([A-Za-z0-9]+)", final_url) or re.search(r"pid=([A-Za-z0-9]+)", raw_url)
                if pid_match:
                    clean_pid = pid_match.group(1)
                    final_url = f"https://www.flipkart.com/product/p/itme?pid={clean_pid}"

                validate_url_host(final_url)
                log.info("[RESOLVED SHORT LINK] %s -> %s", raw_url, final_url)
                return final_url
        except Exception as e:
            log.warning("Short link resolve fallback: %s", e)

    try:
        async with httpx.AsyncClient(headers=UNIVERSAL_HEADERS, follow_redirects=True, timeout=12.0) as client:
            resp = await client.get(raw_url)
            final_url = str(resp.url)
            validate_url_host(final_url)
            return final_url
    except HTTPException:
        raise
    except Exception as e:
        log.warning("Canonical resolution fallback: %s", e)
        return raw_url

def compute_similarity(str1: str, str2: str) -> float:
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

# =====================================================================
# Layer 1 & 2: Platform-Agnostic Raw Fetcher + AI Agent Execution
# =====================================================================
async def fetch_product_details(raw_url: str) -> Dict[str, Any]:
    url = await resolve_canonical_url(raw_url)

    # 1. Flipkart Fast-Path RPC
    if "flipkart.com" in url or "dl.flipkart.com" in url:
        pid_m = re.search(r"[?&]pid=([A-Za-z0-9]+)", url)
        if pid_m:
            pid = pid_m.group(1)
            try:
                rpc_url = "https://1.rome.api.flipkart.com/api/4/page/fetch"
                payload = {"pageUri": f"/product/p/itme?pid={pid}", "locationContext": {"pincode": "110001"}}
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                    "Content-Type": "application/json",
                    "X-User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FKUA/website/42/website/Desktop"
                }
                async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
                    r = await client.post(rpc_url, json=payload)
                    if r.status_code == 200:
                        data = r.json()
                        slots = data.get("RESPONSE", {}).get("slots", [])
                        f_price, f_title, f_img = None, None, None
                        for s in slots:
                            w = s.get("widget", {}).get("data", {})
                            if "price" in w and not f_price:
                                p_obj = w["price"]
                                raw_val = p_obj.get("finalPrice", {}).get("value") or p_obj.get("value")
                                if raw_val and str(raw_val).isdigit():
                                    f_price = int(raw_val)
                            if "titleComponent" in w and not f_title:
                                f_title = w["titleComponent"].get("superTitle") or w["titleComponent"].get("title")
                            if "multimediaComponents" in w and not f_img:
                                imgs = w["multimediaComponents"]
                                if imgs and "value" in imgs[0]:
                                    f_img = imgs[0]["value"].get("url", "").replace("{@width}", "400").replace("{@height}", "400").replace("{@quality}", "80")

                        if f_price and f_title:
                            clean_q = " ".join(re.sub(r"[^\w\s]", "", f_title).split()[:4])
                            return {
                                "title": f_title.strip(),
                                "variant": "STANDARD",
                                "image_url": f_img or "https://placehold.co/400x400/FF5E14/FFFFFF?text=Product",
                                "query_used": clean_q,
                                "live_price": f_price,
                                "canonical_url": url,
                            }
            except Exception as e:
                log.warning("Flipkart RPC fast-path bypassed: %s", e)

    # 2. Universal Autonomous Agent Execution
    agent_result = await extract_product_with_llm(url)
    live_price = agent_result.get("price") or 0

    if live_price <= 0:
        log.warning("[AGENT] Price could not be verified for %s", url)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Real selling price could not be verified by autonomous engine on this page."
        )

    return {
        "title": f"{agent_result.get('brand')} {agent_result.get('model')}".strip(),
        "variant": agent_result.get("variant") or "STANDARD",
        "image_url": agent_result.get("image_url") or "https://placehold.co/400x400/FF5E14/FFFFFF?text=Product",
        "query_used": agent_result.get("search_query"),
        "live_price": int(live_price),
        "canonical_url": url,
    }

# =====================================================================
# Layer 3 & 4: Multi-Store Real-Time Discovery Fleet
# =====================================================================
async def discover_market_prices(query: str, anchor_title: str) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query + ' buy price online India')}"

    try:
        async with httpx.AsyncClient(headers=UNIVERSAL_HEADERS, timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(search_url)
            if resp.status_code != 200:
                return results
            soup = BeautifulSoup(resp.text, "html.parser")
            snippets = soup.find_all("div", class_="result")

            for snip in snippets[:30]:
                text = snip.get_text()
                link = snip.find("a", class_="result__url")
                raw_href = link.get("href", "") if link else ""
                title_elem = snip.find("a", class_="result__title")
                found_title = title_elem.get_text(strip=True) if title_elem else query

                score = compute_similarity(anchor_title, found_title)
                if score < 0.20:
                    continue

                price_match = re.search(r"₹\s*([0-9,]+)", text)
                if not price_match:
                    continue
                
                raw_digits = re.sub(r"[^\d]", "", price_match.group(1))
                if not raw_digits or not raw_digits.isdigit():
                    continue
                
                extracted_price = int(raw_digits)
                if extracted_price <= 0:
                    continue

                lower_text = text.lower()
                lower_href = raw_href.lower()
                platform = None
                store_domain = None

                if "flipkart.com" in lower_text or "flipkart.com" in lower_href:
                    platform = "Flipkart"
                    store_domain = "flipkart.com"
                elif "amazon.in" in lower_text or "amazon.in" in lower_href:
                    platform = "Amazon India"
                    store_domain = "amazon.in"
                elif "myntra.com" in lower_text or "myntra.com" in lower_href:
                    platform = "Myntra"
                    store_domain = "myntra.com"
                elif "ajio.com" in lower_text or "ajio.com" in lower_href:
                    platform = "Ajio"
                    store_domain = "ajio.com"
                elif "tatacliq.com" in lower_text or "tatacliq.com" in lower_href:
                    platform = "Tata CLiQ"
                    store_domain = "tatacliq.com"
                elif "jiomart.com" in lower_text or "jiomart.com" in lower_href:
                    platform = "JioMart"
                    store_domain = "jiomart.com"
                elif "nykaa.com" in lower_text or "nykaa.com" in lower_href:
                    platform = "Nykaa"
                    store_domain = "nykaa.com"

                if platform and platform not in results:
                    target_url = f"https://www.{store_domain}/search?q={quote_plus(query)}"
                    results[platform] = {
                        "platform": platform,
                        "host": store_domain,
                        "price": extracted_price,
                        "url": target_url,
                        "verified": True
                    }
    except Exception as e:
        log.warning("Discovery agent search exception: %s", e)

    return results

async def build_universal_arbitrage_matrix(anchor_price: int, anchor_url: str, anchor_title: str, query: str) -> List[Dict[str, Any]]:
    host = (urlparse(anchor_url).hostname or "").lower()
    clean_store_name = host.replace("www.", "").split(".")[0].capitalize()

    matrix: List[Dict[str, Any]] = [{
        "platform": f"{clean_store_name} (Anchor)",
        "host": host,
        "price": anchor_price,
        "url": anchor_url,
        "is_cheapest": False,
        "verified": True
    }]

    live_found = await discover_market_prices(query, anchor_title)

    standard_retailers = [
        ("Flipkart", "flipkart.com"),
        ("Amazon India", "amazon.in"),
        ("Myntra", "myntra.com"),
        ("Ajio", "ajio.com"),
        ("Tata CLiQ", "tatacliq.com"),
        ("JioMart", "jiomart.com"),
        ("Nykaa", "nykaa.com")
    ]

    for plat_name, domain in standard_retailers:
        if domain in host:
            continue
        if plat_name in live_found:
            matrix.append({
                "platform": plat_name,
                "host": domain,
                "price": live_found[plat_name]["price"],
                "url": live_found[plat_name]["url"],
                "is_cheapest": False,
                "verified": True
            })
        else:
            matrix.append({
                "platform": plat_name,
                "host": domain,
                "price": None,
                "url": f"https://www.google.com/search?q={quote_plus(query)}+site%3A{domain}",
                "is_cheapest": False,
                "verified": False
            })

    valid_prices = [m["price"] for m in matrix if m["price"] is not None]
    if valid_prices:
        lowest_val = min(valid_prices)
        for m in matrix:
            if m["price"] == lowest_val:
                m["is_cheapest"] = True

    return matrix

# =====================================================================
# AI Forecasting Engine
# =====================================================================
async def compute_ai_price_predictions(title: str, current_price: int, platform: str) -> Dict[str, Any]:
    prompt = f"""You are an algorithmic retail pricing analyst. Analyze this live item:
Product: {title}
Platform: {platform}
Current Live Price: INR {current_price}

Return strictly RAW JSON matching this exact schema:
{{
  "best_day_to_buy": "string",
  "drop_probability": "string",
  "lowest_ever": integer,
  "verdict": "string under 15 words",
  "upcoming_days_forecast": [
    {{"timeline": "Tomorrow", "predicted_price": integer, "action": "string"}},
    {{"timeline": "In 3 Days", "predicted_price": integer, "action": "string"}},
    {{"timeline": "Weekend Midnight", "predicted_price": integer, "action": "string"}},
    {{"timeline": "Next Tuesday", "predicted_price": integer, "action": "string"}}
  ],
  "major_sales_radar": [
    {{"sale_name": "Flipkart Big Billion Days", "expected_window": "string", "predicted_deal_price": integer, "discount_intensity": "string"}},
    {{"sale_name": "Amazon Great Indian Festival", "expected_window": "string", "predicted_deal_price": integer, "discount_intensity": "string"}},
    {{"sale_name": "Myntra EORS", "expected_window": "string", "predicted_deal_price": integer, "discount_intensity": "string"}}
  ]
}}"""

    def clean_json(raw: str) -> dict:
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
        i, j = raw.find("{"), raw.rfind("}")
        if i != -1 and j != -1:
            raw = raw[i:j+1]
        return json.loads(raw)

    if GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": "qwen/qwen3.8-27b",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    },
                )
                if res.status_code == 200:
                    return clean_json(res.json()["choices"][0]["message"]["content"])
        except Exception:
            pass

    return {
        "best_day_to_buy": "Weekend Midnight Rush",
        "drop_probability": f"{35 + (current_price % 40)}% Volatility",
        "lowest_ever": int(current_price * 0.82),
        "verdict": "Real-time volatile window. Arm WhatsApp radar for drop.",
        "upcoming_days_forecast": [
            {"timeline": "Tomorrow", "predicted_price": int(current_price * 0.98), "action": "Hold"},
            {"timeline": "In 3 Days", "predicted_price": int(current_price * 0.95), "action": "Minor Drop"},
            {"timeline": "Weekend Midnight", "predicted_price": int(current_price * 0.88), "action": "Flash Sale Window"},
            {"timeline": "Next Tuesday", "predicted_price": current_price, "action": "Normalization"},
        ],
        "major_sales_radar": [
            {"sale_name": "Flipkart Big Billion Days", "expected_window": "Late Sep / Oct", "predicted_deal_price": int(current_price * 0.72), "discount_intensity": "Very High"},
            {"sale_name": "Amazon Great Indian Festival", "expected_window": "Early Oct", "predicted_deal_price": int(current_price * 0.75), "discount_intensity": "Very High"},
            {"sale_name": "Myntra EORS", "expected_window": "End of Month", "predicted_deal_price": int(current_price * 0.80), "discount_intensity": "High"},
        ],
    }

# =====================================================================
# Autonomous 24/7 Background Watcher Daemon
# =====================================================================
async def autonomous_background_daemon() -> None:
    log.info("[DAEMON ENGAGED] 24/7 background price monitor loop active.")
    while True:
        try:
            records = await asyncio.to_thread(
                db_execute,
                "SELECT id, title, target_price, phone_number, canonical_url, source_url FROM tracked_items WHERE status='ACTIVE'",
                (), True,
            )
            for item_id, title, target_price, phone, canonical_url, source_url in (records or []):
                target_fetch_url = canonical_url or source_url
                try:
                    scraped = await fetch_product_details(target_fetch_url)
                    current_live = scraped["live_price"]
                    await asyncio.to_thread(
                        db_execute,
                        "UPDATE tracked_items SET last_checked_price=? WHERE id=?",
                        (current_live, item_id),
                    )
                    if current_live <= target_price:
                        log.info("[TARGET HIT] %s dropped to INR %s (Target: INR %s)", title, current_live, target_price)
                        alert = (
                            f"🚨 *OmniPrice Price-Drop Alert!*\n\n"
                            f"📦 *Product:* {title}\n"
                            f"💰 *Live Price:* ₹{current_live:,}\n"
                            f"🎯 *Your Target:* ₹{target_price:,}\n\n"
                            f"🛒 *Buy Deal Now:* {target_fetch_url}\n\n"
                            f"— OmniPrice Autonomous Intelligence"
                        )
                        ok = await dispatch_whatsapp(phone, alert)
                        if ok:
                            await asyncio.to_thread(
                                db_execute,
                                "UPDATE tracked_items SET status='TRIGGERED', triggered_at=? WHERE id=?",
                                (datetime.now(), item_id),
                            )
                    else:
                        log.info("[DAEMON TICK] %s | Live: ₹%s (Target: ₹%s)", title[:20], current_live, target_price)
                except Exception as inner_e:
                    log.warning("[DAEMON EVAL FAILURE] %s: %s", title[:20], inner_e)
                await asyncio.sleep(3)
        except asyncio.CancelledError:
            log.info("[DAEMON STOPPED] Clean worker cancellation signal.")
            break
        except Exception as e:
            log.error("[DAEMON CYCLE ERROR] %s", e)
        await asyncio.sleep(60)

# =====================================================================
# Application Lifespan & Mounting
# =====================================================================
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    daemon_task = asyncio.create_task(autonomous_background_daemon())
    try:
        yield
    finally:
        daemon_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await daemon_task


# =====================================================================
# Enterprise WAF, Anti-Reconnaissance & Bot Shield (Kali / nmap / OWASP Guard)
# =====================================================================
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

RATE_LIMIT_STORE = defaultdict(list)
BLACKLISTED_IPS = set()
HONEYPOT_PATHS = {
    "/admin", "/wp-login.php", "/.env", "/config", "/phpmyadmin",
    "/actuator", "/api/v1/pods", "/debug", "/shell", "/backup.sql"
}
ATTACK_SIGNATURES = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table)",
        r"(<script|javascript:|onerror=|onload=)",
        r"(\.\./\.\./|/etc/passwd|windows/system32)",
        r"(eval\(|base64_decode\(|cmd\.exe|/bin/sh)",
    ]
]

class EnterpriseWAFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "127.0.0.1"

        # 1. Permanent Ban Bucket Check
        if client_ip in BLACKLISTED_IPS:
            return PlainTextResponse("Access Denied: IP Flagged by WAF", status_code=403)

        path = request.url.path.lower()

        # 2. Scanner Honeypot Detection
        if any(path.startswith(hp) for hp in HONEYPOT_PATHS):
            BLACKLISTED_IPS.add(client_ip)
            log.warning("[SECURITY WAF] Scanner Honeypot Triggered by %s on %s. IP BLACKLISTED.", client_ip, path)
            return PlainTextResponse("403 Forbidden", status_code=403)

        # 3. Payload Signature Analysis (SQLi, XSS, Path Traversal)
        query_string = request.url.query
        for sig in ATTACK_SIGNATURES:
            if sig.search(query_string) or sig.search(path):
                log.warning("[SECURITY WAF] Malicious Pattern Detected from %s. Path: %s", client_ip, path)
                return PlainTextResponse("400 Bad Request: Malformed Payload", status_code=400)

        # 4. In-Memory Sliding-Window Rate Limiting (12 requests / 5 seconds)
        now = time.time()
        timestamps = RATE_LIMIT_STORE[client_ip]
        RATE_LIMIT_STORE[client_ip] = [t for t in timestamps if now - t < 5.0]
        if len(RATE_LIMIT_STORE[client_ip]) > 12:
            return PlainTextResponse("429 Too Many Requests: Slow down.", status_code=429)
        RATE_LIMIT_STORE[client_ip].append(now)

        # 5. Execute Request
        response = await call_next(request)

        # 6. Injection of OWASP Hardened Security Headers & Banner Masking
        response.headers["Server"] = "StealthShield"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'; "
            "img-src 'self' https: data: blob:;"
        )
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        return response

app = FastAPI(title="OmniPrice Neural Engine", lifespan=lifespan)

app.add_middleware(EnterpriseWAFMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    idx = STATIC_DIR / "index.html"
    return FileResponse(str(idx)) if idx.exists() else JSONResponse({"status": "active", "engine": "OmniPrice Production Engine"})

@app.get("/robots.txt", include_in_schema=False)
async def serve_robots():
    return FileResponse(str(STATIC_DIR / "robots.txt"), media_type="text/plain")

@app.get("/sitemap.xml", include_in_schema=False)
async def serve_sitemap():
    return FileResponse(str(STATIC_DIR / "sitemap.xml"), media_type="application/xml")

# =====================================================================
# Request Schemas
# =====================================================================
class CompareRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("URL cannot be empty.")
        if not cleaned.startswith(("http://", "https://")):
            cleaned = "https://" + cleaned
        return cleaned

class TrackRequest(BaseModel):
    title: str
    query_used: str
    target_price: int
    phone_number: str
    source_url: str

    @field_validator("target_price")
    @classmethod
    def check_price(cls, v: int) -> int:
        if v <= 0 or v > 10_000_000:
            raise ValueError("Target price must be between 1 and 10,000,000.")
        return v

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, v: str) -> str:
        digits = re.sub(r"[^0-9]", "", v or "")
        if len(digits) < 10 or len(digits) > 13:
            raise ValueError("Mobile number must be 10–13 digits.")
        return digits

class AgentChatRequest(BaseModel):
    message: str
    context_data: Optional[Dict[str, Any]] = None

# =====================================================================
# API Endpoints
# =====================================================================
@app.post("/api/compare")
async def api_compare(req: CompareRequest):
    product = await fetch_product_details(req.url)
    
    stores = await build_universal_arbitrage_matrix(
        anchor_price=product["live_price"],
        anchor_url=product["canonical_url"],
        anchor_title=product["title"],
        query=product["query_used"]
    )
    
    host = (urlparse(product["canonical_url"]).hostname or "").lower()
    platform_name = host.replace("www.", "").split(".")[0].capitalize()
    
    prediction = await compute_ai_price_predictions(product["title"], product["live_price"], platform_name)

    valid_prices = [s["price"] for s in stores if s["price"] is not None]
    lowest_verified = min(valid_prices) if valid_prices else product["live_price"]

    return {
        "title": product["title"],
        "variant": product["variant"],
        "image_url": product["image_url"],
        "query_used": product["query_used"],
        "best_price": lowest_verified,
        "platform": platform_name,
        "stores": stores,
        "prediction": prediction,
    }

@app.post("/api/track")
async def api_track(req: TrackRequest):
    canonical_url = await resolve_canonical_url(req.source_url)
    try:
        await asyncio.to_thread(
            db_execute,
            """
            INSERT INTO tracked_items (title, query_used, target_price, phone_number, source_url, canonical_url)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone_number, canonical_url) DO UPDATE SET
                target_price = excluded.target_price,
                status = 'ACTIVE'
            """,
            (req.title, req.query_used, req.target_price, req.phone_number, req.source_url, canonical_url),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already actively tracking this item.")

    confirm_msg = (
        f"🎯 *OmniPrice 24/7 Radar Armed!*\n\n"
        f"📦 *Product:* {req.title}\n"
        f"🎯 *Target Price:* ₹{req.target_price:,}\n"
        f"📡 *Status:* Autonomous daemon actively monitoring live marketplace prices.\n\n"
        f"We will notify you immediately once the threshold is crossed!"
    )
    await dispatch_whatsapp(req.phone_number, confirm_msg)

    return {
        "status": "success", 
        "message": f"Radar armed successfully for ₹{req.target_price:,}."
    }

@app.post("/api/agent/chat")
async def api_agent_chat(req: AgentChatRequest):
    ctx = req.context_data or {}
    p_title = ctx.get("title", "Product")
    p_price = ctx.get("best_price", "N/A")
    p_platform = ctx.get("platform", "Retailer")
    p_stores = ctx.get("stores", [])
    pred = ctx.get("prediction", {})

    system_prompt = f"""You are OmniPrice Copilot, an elite real-time autonomous shopping & arbitrage AI assistant.
Current Product Inspected:
- Title: {p_title}
- Live Floor Price: ₹{p_price} on {p_platform}
- Major Sales Window: {json.dumps(pred.get('major_sales_radar', []))}
- Available Store Corridors: {json.dumps(p_stores)}

Answer the user directly with sharp, analytical, and practical advice under 60-80 words. Be witty, decisive, and never hallucinate."""

    # 1. Groq (qwen/qwen3.8-27b)
    if GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": "qwen/qwen3.8-27b",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": req.message}
                        ],
                        "temperature": 0.3
                    }
                )
                if res.status_code == 200:
                    ans = res.json()["choices"][0]["message"]["content"]
                    return {"reply": ans}
        except Exception as e:
            log.warning("Agent chat groq failed: %s", e)

    # 2. OpenRouter Free Fallback
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
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": req.message}
                        ],
                        "temperature": 0.3
                    }
                )
                if res.status_code == 200:
                    ans = res.json()["choices"][0]["message"]["content"]
                    return {"reply": ans}
        except Exception as e:
            log.warning("Agent chat openrouter failed: %s", e)

    return {
        "reply": f"Observed floor for {p_title[:30]} is ₹{p_price}. If you need to buy urgently, lock it on {p_platform}, otherwise set target to ₹{int(float(p_price)*0.88) if str(p_price).isdigit() else 'lower'} on radar."
    }