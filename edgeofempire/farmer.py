#!/usr/bin/env python3
"""
Edge of Empire Telegram Mini-App Auto-Farmer
Mendukung penambangan strategi kerajaan & penarikan USDT:
1. Auto-Sync State Desa (Gold, Elixir, Dark Elixir, Gems)
2. Auto-Collect Tambang Emas & Kolektor Elixir (/api/collectRes)
3. Auto-Claim Hasil Gerobak Jarahan (/api/cart/claim)
4. Auto-Claim Perbendaharaan Kastil (/api/treasury/claim)
5. Auto-Spin Roda Keberuntungan (/api/luck/spin)
"""

import os
import sys
import time
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
API_BASE = "https://edgeofempire.club/api"

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
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_headers(cfg):
    headers = {
        "Origin": "https://edgeofempire.club",
        "Referer": "https://edgeofempire.club/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json"
    }
    init_data = cfg.get("init_data", "")
    if init_data:
        headers["X-Tg-Init"] = init_data
    return headers

def run_farmer():
    log("==================================================")
    log("   EDGE OF EMPIRE AUTO-FARMER (GOLD/ELIXIR/USDT)  ")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            init_data = cfg.get("init_data", "")
            if not init_data:
                log("init_data kosong! Menunggu auto_generator menginjeksi token...")
                time.sleep(30)
                continue

            player = cfg.get("player_id", "tg_7672016530")
            headers = get_headers(cfg)
            body = {"player": player}

            # 1. Fetch State
            r_state = requests.get(f"{API_BASE}/state?player={player}", headers=headers, timeout=15)
            if r_state.status_code != 200:
                log(f"Gagal memuat status kerajaan (HTTP {r_state.status_code}): {r_state.text[:120]}")
                time.sleep(60)
                continue

            data = r_state.json()
            st = data.get("state", {})
            res = st.get("res", {})
            gold = res.get("gold", 0)
            elixir = res.get("elixir", 0)
            dark = res.get("dark", 0)
            gems = res.get("gems", 0)
            trophies = st.get("trophies", 0)

            log(f"🏰 [KERAJAAN] 🪙 Emas: {gold:,} | 💧 Elixir: {elixir:,} | 🔮 Dark: {dark:,} | 💎 Gems: {gems} | 🏆 Tropi: {trophies}")

            # 2. Auto-Collect Tambang & Kolektor
            if cfg.get("auto_collect", True):
                for r_type, label in [("gold", "Emas"), ("elixir", "Elixir")]:
                    try:
                        r_coll = requests.post(f"{API_BASE}/collectRes", json={"player": player, "res": r_type}, headers=headers, timeout=10)
                        if r_coll.status_code == 200:
                            c_data = r_coll.json()
                            if c_data.get("ok"):
                                log(f"🌾 [PANEN] Berhasil panen produksi {label} dari tambang!")
                    except Exception as ce:
                        log(f"Error panen {label}: {ce}")

            # 3. Auto-Claim Fitur Tambahan (Cart, Treasury, Luck)
            if cfg.get("auto_claims", True):
                # Gerobak jarahan
                try:
                    r_cart = requests.post(f"{API_BASE}/cart/claim", json=body, headers=headers, timeout=10)
                    if r_cart.status_code == 200 and r_cart.json().get("ok"):
                        log("🛒 [GEROBAK] Jarahan gerobak berhasil diklaim!")
                except Exception:
                    pass

                # Perbendaharaan
                try:
                    r_tres = requests.post(f"{API_BASE}/treasury/claim", json=body, headers=headers, timeout=10)
                    if r_tres.status_code == 200 and r_tres.json().get("ok"):
                        log("👑 [PERBENDAHARAAN] Hadiah kastil berhasil diklaim!")
                except Exception:
                    pass

                # Putaran Keberuntungan
                try:
                    r_luck = requests.post(f"{API_BASE}/luck/spin", json=body, headers=headers, timeout=10)
                    if r_luck.status_code == 200 and r_luck.json().get("ok"):
                        log("🎰 [LUCKY SPIN] Putaran gratis berhasil dieksekusi!")
                except Exception:
                    pass

            # Interval sleep
            interval = cfg.get("check_interval_seconds", 600)
            log(f"💤 Siklus selesai. Tidur {interval // 60} menit sebelum siklus panen berikutnya...\n")
            time.sleep(interval)

        except Exception as e:
            log(f"Error pada loop utama Edge of Empire: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_farmer()
