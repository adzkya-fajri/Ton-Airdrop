#!/usr/bin/env python3
"""
StarNex Lottery (@lot_tery_bot) Auto-Farmer & Instant WD Daemon
Telethon MTProto Native Client:
- Auto Daily Spins Claim (+1 to +5 Spins)
- Balance tracking (GRAM & SNX)
- Auto Withdraw GRAM to TON Wallet when threshold (>= 0.2 GRAM) is reached.
"""

import os
import sys
import time
import json
import re
import asyncio
from datetime import datetime
from telethon import TelegramClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
SESSION_FILE = os.path.join(BASE_DIR, "starnex_session")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
            f.flush()
    except Exception:
        pass

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "bot_username": "lot_tery_bot",
        "min_withdraw_gram": 0.2,
        "cycle_interval_seconds": 1800,
        "auto_claim": True
    }

async def run_cycle():
    cfg = load_config()
    bot_user = cfg.get("bot_username", "lot_tery_bot")

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        log("❌ Error: Sesi Telegram starnex_session tidak terotorisasi.")
        await client.disconnect()
        return

    try:
        bot = await client.get_entity(bot_user)

        # 1. Ambil info profil & saldo
        await client.send_message(bot, "💸 Personal profile")
        await asyncio.sleep(2.5)
        msgs = await client.get_messages(bot, limit=2)
        txt = msgs[0].text if msgs else ""

        spins_m = re.search(r"Spins[:\*]+\s*(\d+)", txt, re.IGNORECASE)
        gram_m = re.search(r"GRAM[:\*]+\s*([\d.]+)", txt, re.IGNORECASE)
        snx_m = re.search(r"SNX[:\*]+\s*([\d.]+)", txt, re.IGNORECASE)

        spins = int(spins_m.group(1)) if spins_m else 0
        gram = float(gram_m.group(1)) if gram_m else 0.0
        snx = float(snx_m.group(1)) if snx_m else 0.0

        log(f"🎰 [Status] Saldo GRAM: {gram:.4f} GRAM | Spins: {spins} Tiket | Saldo SNX: {snx:.2f} 🪙")

        # 2. Klaim free spins harian
        if cfg.get("auto_claim", True):
            await client.send_message(bot, "🎁 Free spins")
            await asyncio.sleep(2.0)
            log("🎁 [Daily] Memeriksa & mengklaim free spins harian...")

        # 3. Auto WD jika GRAM >= min_withdraw_gram
        min_wd = float(cfg.get("min_withdraw_gram", 0.2))
        w_addr = cfg.get("ton_wallet_address", "")
        if gram >= min_wd and w_addr:
            log(f"🚀 [AUTO-WD] Saldo {gram:.4f} GRAM >= {min_wd:.2f} GRAM! Memproses penarikan...")
            await client.send_message(bot, "💎 GRAM and payments")
            await asyncio.sleep(2.0)
            msgs = await client.get_messages(bot, limit=2)
            for m in msgs:
                if m.reply_markup:
                    await m.click(text="📤 Withdraw GRAM")
                    await asyncio.sleep(2.0)
                    await client.send_message(bot, f"{gram:.4f}")
                    await asyncio.sleep(2.0)
                    await client.send_message(bot, w_addr)
                    log(f"✅ [AUTO-WD] Permintaan penarikan {gram:.4f} GRAM terkirim ke {w_addr}!")
                    break

    except Exception as e:
        log(f"⚠️ Error siklus: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

async def main_loop():
    log("=== StarNex Lottery Auto-Farmer Daemon Dimulai ===")
    while True:
        try:
            await run_cycle()
        except Exception as e:
            log(f"Error loop: {e}")
        time.sleep(1800)

if __name__ == "__main__":
    asyncio.run(main_loop())
