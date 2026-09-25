import httpx

GATEWAY_URL = "http://127.0.0.1:5001/send-message"

async def send_whatsapp_alert(phone: str, product_title: str, current_price: int, target_price: int, buy_url: str) -> bool:
    """
    Dispatches a real WhatsApp message using our local self-hosted Baileys gateway.
    """
    message_text = (
        f"🚨 *OmniPrice Price-Drop Alert!*\n\n"
        f"📦 *Product:* {product_title}\n"
        f"💰 *Current Price:* ₹{current_price:,}\n"
        f"🎯 *Your Target:* ₹{target_price:,}\n\n"
        f"🛒 *Buy Deal Now:* {buy_url}\n\n"
        f"— OmniPrice Autonomous Intelligence"
    )

    payload = {
        "phone": phone,
        "message": message_text
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(GATEWAY_URL, json=payload)
            if res.status_code == 200:
                print(f"\n[WHATSAPP SUCCESS] Delivered to {phone} via Local Gateway!\n")
                return True
            else:
                print(f"\n[GATEWAY ERROR] {res.status_code}: {res.text}\n")
                return False
    except Exception as e:
        print(f"\n[GATEWAY CONNECTION FAILED] Is the Node.js server running on 5001? Error: {e}\n")
        return False