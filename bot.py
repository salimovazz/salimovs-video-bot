#!/usr/bin/env python3
"""
Salimov's AI — Nimagination 8-Frame Motion Video Generator & Full-Stack Bot
Configured for Render.com & 24/7 Cloud Deployment with Auto-Ping Keep-Awake
"""

import os
import sys
import re
import io
import time
import zipfile
import asyncio
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Force IPv4 resolution
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

import requests
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# API Keys (Reads from Render Environment Variables or defaults to yours)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", 10000))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3.5-flash",
]

# --- RENDER HEALTH-CHECK & SELF-PING SERVER ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Salimov's AI Bot is Live & Active 24/7 on Render!")

    def log_message(self, format, *args):
        pass # silent logs

def run_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    print(f"Health-check server running on port {PORT}...", flush=True)
    server.serve_forever()

def keep_awake_loop():
    """Pings the server every 9 minutes so Render never goes to sleep"""
    while True:
        time.sleep(540) # 9 daqiqa
        target_url = RENDER_EXTERNAL_URL if RENDER_EXTERNAL_URL else f"http://127.0.0.1:{PORT}"
        try:
            requests.get(target_url, timeout=10)
            print("[Auto-Ping]: Server muvaffaqiyatli uyg'otildi (24/7 Active)", flush=True)
        except Exception:
            pass

SYSTEM_PROMPT = """Siz "Nimagination" (@nimaginationuz) uslubidagi 8 TA ANIQ KADRLI ILMIY MOTION-VIDEO YARATUVCHI AI DASTURCHISIZ.

SIZNING QAT'IY 8 TA KADR STANDARTINGIZ:
Foydalanuvchi qanday mavzu bersa (masalan: Uran siri, Qora tuynuklar, Mars, Sun'iy intellekt va h.k.), siz aynan Nimagination kanalining 8 ta sahnasini bitta `video.html` faylida yaratasiz:

1. KADR 1: KOSMIK KEMA KOKPITI VA ASTRONAVT QAHRAMON
- Kokpit romi, priborlar paneli, miltillovchi osiloskop.
- Oq skafandrli astronavt (stickman) qo'li bilan oynani ko'rsatadi.
- Yuqori burchakda qora-qizil badge: "nimagination OBUNA BO'LING 🔔".

2. KADR 2: GIGANT ORBITA VA UZOQDAGI QUYOSH
- Kosmos qa'rida charaqlagan sariq Quyosh va ellips shaklidagi ulkan punktir orbita chizig'i.

3. KADR 3: HAYRATLANARLI TAQQOSLASH (INFOGRAFIKA)
- 1 Uran yili ≈ 84 Yer yili! Chapda aylanuvchi orbita, o'ngda 84 yoshdagi chol, qizil-oq kalendar va tug'ilgan kun torti.

4. KADR 4: NOODATIY FIZIK HOLAT (98° QIYALIK)
- Sayyora yonboshlab aylanishi, qutblar: "Qutb: yillab yorug'lik", "Qutb: yillab qorong'ilik", Quyosh nuri vektori.

5. KADR 5: SAYYORANING TAShQI GO'ZALLIGI
- Katta moviy-yashil sayyora, vertikal xira halqalar va uning yonidan uchib o'tuvchi kosmik kema. Qora shaffof kapsula: "moviy-yashil tus", "Xira halqalar".

6. KADR 6: EKSTREMAL HARORAT
- Muzli ko'k tuman foni, katta termometr belgisi va ulkan raqam: "≈ -224 °C atmosferaning eng sovuq hududlarida".

7. KADR 7: SODDALASHTIRILGAN ILMIY MODEL (ICHKI KESMA)
- Sayyoraning qatlamlari kesmasi (Atmosfera, H2O/NH3/CH4 qaynoq muz mantiyasi, toshli yadro). Yozuv: "nihoyatda issiq va zich holatda".

8. KADR 8: INTERAKTIV YAKUNIY SAVOL (A / B)
- Katta savol: "Sizga qaysi biri qiziqroq tuyuldi?"
- Ikkita yorqin tugma/karta: [A] Yonboshlab aylanishi va [B] Muz gigantining issiq ichi.

TEXNIK TALABLAR:
- 1920x1080 qat'iy `#stage` va `fit()` masshtabi.
- `render(t)` deterministik vaqt shkalasi (32 soniya, har kadr 4 soniya).
- `easeOutCubic` silliq o'tishlar.
- Web Audio API (Whoosh SFX) va Web Speech API (diktorskiy ovoz).
- MediaRecorder orqali videoni .webm fayl qilib yuklab olish tugmasi.

FAYL FORMATI:
```FILE: video.html
kodi
```
"""

CONVERSATIONS = {}

def call_gemini(messages):
    contents = [
        {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
        {"role": "model", "parts": [{"text": "Tushundim! Men xuddi Nimagination storyboardidagi kabi 8 ta kadrdan iborat to'liq video.html yarataman."}]}
    ]

    for m in messages[-10:]:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["text"]}]})

    last_error = ""
    for model_name in MODELS:
        print(f"[{model_name}] ga so'rov yuborilmoqda...", flush=True)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            resp = requests.post(url, json={"contents": contents}, timeout=110)
            if resp.status_code == 200:
                data = resp.json()
                candidate = data.get("candidates", [{}])[0]
                text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
                if text:
                    print(f"[{model_name}] Javob tayyor ({len(text)} belgi)", flush=True)
                    return text
            else:
                last_error = f"{model_name} HTTP {resp.status_code}: {resp.text[:100]}"
                print(f"[{model_name}] Xato: {last_error}", flush=True)
        except Exception as e:
            last_error = f"{model_name} Exception: {e}"
            print(f"[{model_name}] Ulanish xatosi: {e}", flush=True)

    return f"Kechirasiz, model javob berishda xatolik yuz berdi: {last_error}"

def extract_files_from_text(text):
    pattern = r"```(?:FILE:|file:|[\w+-]+:)\s*([^\n\r]+)[\r\n](.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    files = {}
    for filename, content in matches:
        filename = filename.strip()
        filename = re.sub(r"^[#/ ]+", "", filename).strip()
        if filename:
            files[filename] = content
    return files

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    CONVERSATIONS[chat_id] = []
    welcome_text = (
        "🎬 <b>Nimagination 8-Kadrli Video Yaratuvchi Botga xush kelibsiz!</b>\n\n"
        "Menga shunchaki mavzu ayting (masalan: <i>\"Uran siri\"</i> yoki <i>\"Qora tuynuk\"</i>).\n\n"
        "Men xuddi rasmdagidek <b>8 ta kadr</b> bilan:\n"
        "1. 🚀 Kokpit va Astronavt qahramon\n"
        "2. ☀️ Quyosh va gigant orbita\n"
        "3. 🎂 84 yillik taqqoslash infografikasi\n"
        "4. 🌀 98° qiyalik va qutb yorug'ligi\n"
        "5. 🪐 Moviy-yashil sayyora va xira halqalar\n"
        "6. ❄️ -224 °C termometr animatsiyasi\n"
        "7. 🔬 Soddalashtirilgan ichki qatlamlar kesmasi\n"
        "8. ❓ Interaktiv A / B savol\n\n"
        "Barchasini diktor ovozi, SFX va eksport tugmasi bilan <b>video.html</b> qilib tashlab beraman!"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return

    chat_id = update.effective_chat.id
    print(f"\n[Yangi so'rov - Chat {chat_id}]: {user_text}", flush=True)

    if chat_id not in CONVERSATIONS:
        CONVERSATIONS[chat_id] = []

    CONVERSATIONS[chat_id].append({"role": "user", "text": user_text})

    status_msg = await update.message.reply_text("🎬 Nimagination uslubidagi 8 ta kadr yig'ilmoqda...")

    async def keep_typing():
        try:
            while True:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VIDEO)
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    typing_task = asyncio.create_task(keep_typing())

    try:
        loop = asyncio.get_running_loop()
        ai_response = await loop.run_in_executor(None, call_gemini, CONVERSATIONS[chat_id])
    finally:
        typing_task.cancel()

    CONVERSATIONS[chat_id].append({"role": "model", "text": ai_response})

    extracted_files = extract_files_from_text(ai_response)
    print(f"[Natija]: {len(extracted_files)} ta fayl aniqlandi: {list(extracted_files.keys())}", flush=True)

    try:
        await status_msg.delete()
    except Exception:
        pass

    video_html_key = next((k for k in extracted_files if k.lower().endswith(".html")), None)

    if video_html_key:
        html_content = extracted_files[video_html_key]
        html_buffer = io.BytesIO(html_content.encode('utf-8'))
        html_buffer.seek(0)
        
        await update.message.reply_text(
            "🎬 <b>Nimagination 8-Kadrli Video Tayyor Bo'ldi!</b>\n\n"
            "Faylni yuklab olib Chrome/brauzerda oching 👇",
            parse_mode=ParseMode.HTML
        )
        await context.bot.send_document(
            chat_id=chat_id,
            document=html_buffer,
            filename=video_html_key,
            caption="🎥 Play tugmasini bosing — diktor ovozi, SFX va 8 kadrli animatsiya bilan o'ynaydi!"
        )

def main():
    print("Salimov's AI Bot ishga tushmoqda...", flush=True)
    
    # Start health server and auto-ping thread for Render.com
    threading.Thread(target=run_health_server, daemon=True).start()
    threading.Thread(target=keep_awake_loop, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot muvaffaqiyatli ulandi! Polling boshlandi...", flush=True)
    app.run_polling()

if __name__ == "__main__":
    main()
