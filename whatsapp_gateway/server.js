const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require("@whiskeysockets/baileys");
const qrcode = require("qrcode-terminal");
const express = require("express");
const bodyParser = require("body-parser");

const app = express();
app.use(bodyParser.json());

let sock = null;

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("auth_info_baileys");

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("\n=======================================================");
      console.log("📲 SCAN THIS QR CODE WITH YOUR NORMAL WHATSAPP:");
      console.log("=======================================================\n");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "close") {
      const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log("[GATEWAY] Connection closed. Reconnecting:", shouldReconnect);
      if (shouldReconnect) {
        connectToWhatsApp();
      }
    } else if (connection === "open") {
      console.log("\n[GATEWAY ONLINE] ✅ WhatsApp Web Connected Successfully!\n");
    }
  });
}

// REST Endpoint to send message from Python
app.post("/send-message", async (req, res) => {
  const { phone, message } = req.body;

  if (!sock) {
    return res.status(500).json({ status: "error", message: "WhatsApp socket not initialized" });
  }

  try {
    // Format to WhatsApp JID (e.g. 919876543210@s.whatsapp.net)
    let cleanPhone = phone.replace(/[^0-9]/g, "");
    if (cleanPhone.length === 10) cleanPhone = "91" + cleanPhone;
    const jid = `${cleanPhone}@s.whatsapp.net`;

    await sock.sendMessage(jid, { text: message });
    console.log(`[DISPATCHED] Message sent to ${jid}`);
    return res.json({ status: "success", delivered_to: jid });
  } catch (err) {
    console.error("[SEND ERROR]", err);
    return res.status(500).json({ status: "error", error: err.message });
  }
});

const PORT = 5001;
app.listen(PORT, () => {
  console.log(`[GATEWAY SERVER] Running on http://127.0.0.1:${PORT}`);
  connectToWhatsApp();
});