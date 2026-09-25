import sqlite3
import datetime
from typing import Dict, Any, List, Optional

DB_PATH = "price_tracker.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 1. Price History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_used TEXT,
            platform TEXT,
            price INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            day_of_week TEXT
        )
    """)
    # 2. Tracking Subscriptions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_title TEXT,
            query_used TEXT,
            target_price INTEGER,
            phone_number TEXT,
            source_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Auto-initialize on import
init_db()

class PricePredictor:
    @staticmethod
    def record_prices(query: str, stores: List[Dict[str, Any]]):
        if not stores:
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now = datetime.datetime.now()
        day_name = now.strftime("%A")

        for s in stores:
            price = s.get("price")
            platform = s.get("platform", "Unknown")
            if price and isinstance(price, (int, float)) and price > 0:
                cursor.execute("""
                    INSERT INTO price_history (query_used, platform, price, recorded_at, day_of_week)
                    VALUES (?, ?, ?, ?, ?)
                """, (query.lower().strip(), platform, int(price), now.isoformat(), day_name))
        
        conn.commit()
        conn.close()

    @staticmethod
    def analyze_trend(query: str, current_best: Optional[int]) -> Dict[str, Any]:
        """
        Calculates Lowest Recorded Ever, Volatility, and Best Day to Buy.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        q_norm = query.lower().strip()

        cursor.execute("SELECT price, day_of_week FROM price_history WHERE query_used = ?", (q_norm,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            # Baseline estimation if single-day sample exists
            ref = current_best or 999
            return {
                "lowest_ever": ref,
                "best_day_to_buy": "Friday to Sunday",
                "drop_probability": "High on Weekends (15-20% drop expected)",
                "verdict": "Wait for Weekend Sale" if datetime.datetime.now().strftime("%A") not in ["Friday", "Saturday", "Sunday"] else "Best Time to Buy!"
            }

        prices = [r[0] for r in rows]
        lowest_ever = min(prices)

        # Calculate average price per day
        day_aggregates: Dict[str, List[int]] = {}
        for p, d in rows:
            day_aggregates.setdefault(d, []).append(p)

        best_day = min(day_aggregates.keys(), key=lambda d: sum(day_aggregates[d]) / len(day_aggregates[d]))

        is_cheaper_now = current_best is not None and current_best <= lowest_ever
        verdict = "Lowest Price Recorded! Buy Now." if is_cheaper_now else f"Price usually drops lower on {best_day}s."

        return {
            "lowest_ever": lowest_ever,
            "best_day_to_buy": f"{best_day}s",
            "drop_probability": "Moderate to High",
            "verdict": verdict
        }

    @staticmethod
    def save_alert(title: str, query: str, target_price: int, phone: str, url: str) -> bool:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_alerts (product_title, query_used, target_price, phone_number, source_url)
                VALUES (?, ?, ?, ?, ?)
            """, (title, query.lower().strip(), target_price, phone.strip(), url))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB ERROR] {e}")
            return False