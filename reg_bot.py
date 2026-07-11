#!/usr/bin/env python3
"""
Registration check bot v3 — MULTI CONTAINER PARALLEL.
3 Redroid containers berjalan paralel untuk proses 3 nomor sekaligus.
Email verification & clear data tetap ada.
"""

import asyncio
import subprocess
import re
import sys
import requests
import json
import time
from telethon import TelegramClient, events

BOT_TOKEN = "8857079643:AAHshunNy0KUkWOIql-1BAozk5UDBSCdicQ"
API_ID = 5214566
API_HASH = "03ee5a4be9848535eb9aace996f5202d"

ADB_PORTS = [5555, 5556, 5557]
CONCURRENCY = len(ADB_PORTS)

# Temp mail — auto-created per session
TEMP_EMAIL = None
TEMP_PWD = "Test12345"

client = TelegramClient("reg_bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


# --- Container Pool ---
class ContainerPool:
    def __init__(self, ports):
        self._queue = asyncio.Queue()
        for p in ports:
            self._queue.put_nowait(p)

    async def acquire(self):
        return await self._queue.get()

    def release(self, port):
        self._queue.put_nowait(port)

pool = ContainerPool(ADB_PORTS)

# --- Temp Mail ---
def ensure_temp_mail():
    global TEMP_EMAIL
    r = requests.post("https://api.mail.tm/token", json={"address": TEMP_EMAIL, "password": TEMP_PWD}) if TEMP_EMAIL else None
    if r and r.status_code == 200:
        return r.json()["token"]
    ts = str(int(time.time()))[-6:]
    new_email = f"xentest{ts}@web-library.net"
    r = requests.post("https://api.mail.tm/accounts", json={"address": new_email, "password": TEMP_PWD})
    if r.status_code == 201:
        TEMP_EMAIL = new_email
        r2 = requests.post("https://api.mail.tm/token", json={"address": TEMP_EMAIL, "password": TEMP_PWD})
        if r2.status_code == 200:
            return r2.json()["token"]
    return None

def poll_email_code(token, timeout=90):
    headers = {"Authorization": "Bearer " + token}
    deadline = time.time() + timeout
    requests.delete("https://api.mail.tm/messages", headers=headers)
    while time.time() < deadline:
        r = requests.get("https://api.mail.tm/messages", headers=headers)
        if r.status_code == 200:
            for msg in r.json().get("hydra:member", []):
                mid = msg["@id"]
                r2 = requests.get("https://api.mail.tm" + mid, headers=headers)
                if r2.status_code == 200:
                    body = json.dumps(r2.json())
                    codes = re.findall(r"\b(\d{5,6})\b", body)
                    if codes:
                        return codes[0]
        time.sleep(3)
    return None

# --- ADB Helpers ---
def adb(port, cmd):
    subprocess.run(f"adb -s 127.0.0.1:{port} shell '{cmd}'", shell=True, capture_output=True)

def tap(port, x, y):
    adb(port, f"input tap {x} {y}")

def txt(port, t):
    adb(port, f'input text "{t}"')

def get_ui_texts(port):
    subprocess.run(f"adb -s 127.0.0.1:{port} shell uiautomator dump /sdcard/rb.xml", shell=True, capture_output=True)
    r = subprocess.run(f"adb -s 127.0.0.1:{port} shell cat /sdcard/rb.xml", shell=True, capture_output=True, text=True)
    return re.findall(r'text="([^"]{1,100})"', r.stdout)

def tap_yes(port):
    """Find and tap 'Yes' button via uiautomator"""
    subprocess.run(f"adb -s 127.0.0.1:{port} shell uiautomator dump /sdcard/rb_yes.xml", shell=True, capture_output=True)
    r = subprocess.run(f"adb -s 127.0.0.1:{port} shell cat /sdcard/rb_yes.xml", shell=True, capture_output=True, text=True)
    # Look for "Yes" button bounds
    m = re.search(r'text="Yes"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', r.stdout)
    if m:
        cx = (int(m.group(1)) + int(m.group(3))) // 2
        cy = (int(m.group(2)) + int(m.group(4))) // 2
        subprocess.run(f"adb -s 127.0.0.1:{port} shell input tap {cx} {cy}", shell=True)
        return True
    # Fallback: try common coordinates for "Yes"
    tap(port, 598, 474)
    return False

# --- Core Check ---
async def check_number_full(phone: str, port: int, mail_token: str) -> tuple:
    """Full check on one Redroid container."""
    try:
        adb(port, "pm clear org.telegram.messenger")
        await asyncio.sleep(1)
        adb(port, "am start -n org.telegram.messenger/org.telegram.ui.LaunchActivity")
        await asyncio.sleep(4)
        tap(port, 360, 1036)
        await asyncio.sleep(2)

        cc = phone[1:4]
        num = phone[4:]
        tap(port, 150, 600)
        await asyncio.sleep(0.3)
        txt(port, cc)
        await asyncio.sleep(0.5)
        tap(port, 400, 600)
        await asyncio.sleep(0.3)
        txt(port, num)
        await asyncio.sleep(0.5)
        tap(port, 624, 648)
        await asyncio.sleep(3)

        # Tap "Yes" on confirmation dialog if it appears
        tap_yes(port)
        await asyncio.sleep(10)

        # Wait for real screen (not splash)
        for _ in range(5):
            await asyncio.sleep(1)
            texts_raw = get_ui_texts(port)
            texts = [t for t in texts_raw if t not in (
                "Telegram", "The world's fastest messaging app.",
                "It is free and secure.", "Your messages are protected.",
            )]
            meaningful = [t for t in texts if len(t) > 4 and not t.startswith("http")]
            if len(meaningful) > 0:
                break

        texts = get_ui_texts(port)
        # print(f"  [{port}] SCREEN: {texts}")

        # DETECT ADD_EMAIL early - different UI, don't try to handle it
        all_text_pre = " ".join(texts).lower()
        is_add_email = ("add" in all_text_pre and "email" in all_text_pre) or                        any(t.lower().strip() == "add email" for t in texts)
        if is_add_email:
            return "ADD_EMAIL", None

        # Check email
        if any("email" in t.lower() for t in texts):
            # Input temp email
            tap(port, 200, 420)
            await asyncio.sleep(0.5)
            txt(port, TEMP_EMAIL)
            await asyncio.sleep(1)
            tap(port, 624, 574)
            await asyncio.sleep(5)

            # Wait for code (shorter timeout - mail.tm usually doesn't get Telegram emails)
            code = await asyncio.get_event_loop().run_in_executor(
                None, lambda: poll_email_code(mail_token, 45)
            )
            if code:
                txt(port, code)
                await asyncio.sleep(5)
                texts = get_ui_texts(port)
            else:
                # No code - check if Telegram moved on
                texts = get_ui_texts(port)
                if any("email" in t.lower() for t in texts):
                    # Still asking for email - can't proceed without real email
                    return "EMAIL_VERIFICATION", None

        # Determine result
        all_text = " ".join(texts).lower()
        # print(f"  [{port}] ALL TEXT: {all_text}")

        if "sms fee" in all_text or "payment required" in all_text or "premium" in all_text:
            return "PAYMENT_REQUIRED", None
        elif "enter the code" in all_text or "sent you" in all_text or "verification code" in all_text:
            if "telegram" in all_text:
                return "OTP_APP", None
            return "OTP_SENT", None
        elif "call" in all_text and "phone" in all_text:
            return "CALL_VERIFICATION", None
        elif "invalid" in all_text or "wrong number" in all_text:
            return "INVALID_NUMBER", None
        elif "add" in all_text and "email" in all_text and "please" not in all_text:
            if "choose" in all_text:
                return "EMAIL_VERIFICATION", None
            return "ADD_EMAIL", None
        elif "email" in all_text and "please" in all_text and "add" in all_text:
            return "ADD_EMAIL", None
        elif any("add" in t and "email" in t for t in texts):
            return "ADD_EMAIL", None
        elif "email" in all_text and ("verif" in all_text or "choose" in all_text or "protect" in all_text or "please" in all_text):
            return "EMAIL_VERIFICATION", None
        elif "code" in all_text and ("check" in all_text or "enter" in all_text or "send" in all_text):
            if "telegram" in all_text:
                return "OTP_APP", None
            return "OTP_SENT", None
        elif "wait" in all_text or "loading" in all_text:
            return "UNKNOWN", "Loading"
        elif "next" in all_text or "continue" in all_text:
            return "UNKNOWN", str(texts)
        else:
            return "UNKNOWN", str(texts)

    except Exception as e:
        return "ERROR", str(e)

def emoji_for(result: str) -> str:
    mapping = {
        "OTP_SENT": "✅",
        "OTP_APP": "📱",
        "PAYMENT_REQUIRED": "❌",
        "PAYMENT": "❌",
        "CALL_VERIFICATION": "📞",
        "INVALID_NUMBER": "🚫",
        "EMAIL_VERIFICATION": "📧",
        "ADD_EMAIL": "✉️",
        "EMAIL_ERROR": "📧",
        "TIMEOUT": "⏰",
        "ERROR": "⚠️",
        "UNKNOWN": "❓",
    }
    return mapping.get(result, "❓")

def parse_phone(number: str) -> str:
    number = number.strip().replace(" ", "").replace("-", "").replace("_", "")
    if not number.startswith("+"):
        number = "+" + number
    return number



# --- Bot Handlers ---
@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.reply(
        "🤖 *Registration Check Bot v3 — Multi Container 🔥*\n\n"
        "Kirim daftar nomor telepon (1 nomor per baris).\n"
        "Diproses **3 nomor sekaligus** secara paralel.\n\n"
        "*Hasil yang mungkin:*\n"
        "✅ OTP_SENT — aman, bisa daftar OTP lewat SMS\n"
        "❌ PAYMENT_REQUIRED — kena fee SMS / perlu Premium\n"
        "📞 CALL_VERIFICATION — via telepon\n"
        "📧 EMAIL_VERIFICATION — perlu email verify (otomatis)\n"
        "✉️ ADD_EMAIL — perlu input email (seperti +591)\n"
        "📱 OTP_APP — OTP via aplikasi Telegram\n"
        "🚫 INVALID_NUMBER — nomor salah\n\n"
        "*Contoh:*\n"
        "```\n+6281234567890\n+243802347360\n+60123456789\n```\n\n📲 *Registrasi OTP:*\nKirim `/reg <nomor> <kode>` untuk validasi OTP\nContoh: `/reg +584166047548 12345`",
        parse_mode="markdown"
    )

@client.on(events.NewMessage(pattern="/newmail"))
async def newmail_handler(event):
    global TEMP_EMAIL
    ts = str(int(time.time()))[-6:]
    new_email = f"xentest{ts}@web-library.net"
    TEMP_EMAIL = new_email
    r = requests.post("https://api.mail.tm/accounts", json={"address": TEMP_EMAIL, "password": TEMP_PWD})
    if r.status_code == 201:
        await event.reply(f"✅ New temp email: `{TEMP_EMAIL}`")
    else:
        await event.reply(f"❌ Failed: {r.text[:100]}")

@client.on(events.NewMessage(pattern="/status"))
async def status_handler(event):
    statuses = []
    for p in ADB_PORTS:
        r = subprocess.run(f"adb -s 127.0.0.1:{p} shell echo OK", shell=True, capture_output=True, text=True, timeout=3)
        ok = r.stdout.strip() == "OK"
        statuses.append(f"{'✅' if ok else '❌'} Container {p}")
    await event.reply(
        "🔄 *Bot Status*\n" + "\n".join(statuses) +
        f"\n\n⚡ Paralel: {CONCURRENCY} container\n📧 Email: {TEMP_EMAIL}",
        parse_mode="markdown"
    )

@client.on(events.NewMessage(func=lambda e: not e.text.startswith("/")))
async def numbers_handler(event):
    text = event.text.strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if len(lines) == 0:
        await event.reply("Kirim nomor teleponnya.")
        return

    if len(lines) > 50:
        await event.reply("Maksimal 50 nomor per batch.")
        return

    msg = await event.reply(f"⚡ Memproses {len(lines)} nomor dengan {CONCURRENCY} container paralel...")

    # Buat temp email
    mail_token = ensure_temp_mail()

    sem = asyncio.Semaphore(CONCURRENCY)

    async def check_one(raw_num):
        async with sem:
            port = await pool.acquire()
            try:
                phone = parse_phone(raw_num)
                if not re.match(r'^\+\d{7,15}$', phone):
                    return f"⏭️ `{raw_num}` — format salah"

                result, extra = await check_number_full(phone, port, mail_token)
                emoji = emoji_for(result)
                line = f"{emoji} `{phone}` → {result}"
                return line
            finally:
                pool.release(port)

    # Process in parallel
    tasks = [check_one(num) for num in lines]
    total = len(tasks)
    results = [None] * total
    completed = 0

    # Live progress: send new message each time a result completes
    for coro in asyncio.as_completed(tasks):
        result = await coro
        # Find first None slot and insert
        for i, r in enumerate(results):
            if r is None:
                results[i] = result
                break
        completed += 1

        done_lines = [r for r in results if r is not None]
        live_report = "\n".join(done_lines)
        progress_header = f"⚡ [{completed}/{total}] Memproses {total} nomor dengan {CONCURRENCY} container...\n\n"
        await msg.edit(progress_header + live_report, parse_mode="markdown", link_preview=False)
        await asyncio.sleep(0.5)

    # Final report with summary
    done_lines = [r for r in results if r is not None]
    report = "\n".join(done_lines)

    otp_count = sum(1 for r in done_lines if "OTP_SENT" in r and "OTP_APP" not in r)
    app_count = sum(1 for r in done_lines if "OTP_APP" in r)
    pay_count = sum(1 for r in done_lines if "PAYMENT_REQUIRED" in r or "PAYMENT" in r)
    email_count = sum(1 for r in done_lines if "EMAIL_VERIFICATION" in r or "EMAIL_ERROR" in r)
    add_count = sum(1 for r in done_lines if "ADD_EMAIL" in r)
    other = len(done_lines) - otp_count - app_count - pay_count - email_count - add_count

    footer = f"\n\n📊 *Ringkasan:*\n✅ SMS: {otp_count} / 📱 App: {app_count} / ❌ Fee: {pay_count} / 📧 Email: {email_count} / ✉️ Add: {add_count} / ❓ Lain: {other}"

    await msg.edit(report + footer, parse_mode="markdown", link_preview=False)

print(f"Bot v3 running — {CONCURRENCY} parallel containers on ports {ADB_PORTS}")
client.run_until_disconnected()
