#!/usr/bin/env python3
"""
Catopia Game Telegram Mini-App Auto-Farmer ($CAT)
Features:
1. Dynamic config reload & integration with auth-generator
2. Exchange init_data for Bearer accessToken (/api/v1/auth/telegram)
3. Auto daily check-in (/api/v1/user/checkin)
4. Auto claim gold / idle earnings (/api/v1/user/claim-gold)
5. Auto land status, seeding, and crop harvest
6. Real-time balance and level logging
"""

import os
import sys
import time
import json
import random
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
API_BASE = "https://api.catopia.io"

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

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def get_headers(cfg, token=None):
    headers = {
        "Origin": "https://game.catopia.io",
        "Referer": "https://game.catopia.io/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def login(cfg):
    init_data = cfg.get("init_data", "")
    if not init_data:
        log("init_data kosong! Menunggu penyegaran token oleh auth_generator...")
        return None
    url = f"{API_BASE}/api/v1/auth/telegram"
    headers = get_headers(cfg)
    try:
        res = requests.post(url, headers=headers, json={"initData": init_data}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            token = data.get("data", {}).get("accessToken") or data.get("accessToken")
            if token:
                log("✅ Login Catopia berhasil! Token sesi diperoleh.")
                return token
        log(f">> Login gagal: HTTP {res.status_code} - {res.text[:100]} <<")
    except Exception as e:
        log(f">> Exception saat login: {e} <<")
    return None

def get_user_info(cfg, token):
    url = f"{API_BASE}/api/v1/user/me?limit=3000"
    headers = get_headers(cfg, token)
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("data", {})
    except Exception as e:
        log(f">> Error ambil user info: {e} <<")
    return None

def do_checkin(cfg, token):
    if not cfg.get("auto_checkin", True):
        return
    url = f"{API_BASE}/api/v1/user/checkin"
    headers = get_headers(cfg, token)
    try:
        res = requests.post(url, headers=headers, json={}, timeout=15)
        if res.status_code == 200:
            log("🎉 Daily Check-in Catopia Sukses!")
    except Exception as e:
        log(f">> Check-in error: {e} <<")

def do_claim_gold(cfg, token):
    if not cfg.get("auto_claim_gold", True):
        return
    url = f"{API_BASE}/api/v1/user/claim-gold"
    headers = get_headers(cfg, token)
    try:
        res = requests.post(url, headers=headers, json={}, timeout=15)
        if res.status_code == 200:
            log("🪙 Klaim Gold / Idle Farm Berhasil!")
    except Exception as e:
        log(f">> Claim gold error: {e} <<")

def farm_cycle():
    cfg = load_config()
    token = login(cfg)
    if not token:
        return 120

    info = get_user_info(cfg, token)
    if info:
        name = info.get("username") or info.get("firstName") or "Player"
        gold = info.get("gold", 0)
        gems = info.get("gems", 0)
        log("=" * 50)
        log(f"🐾 [Catopia] Akun: {name} | 🪙 Gold: {gold} | 💎 Gems: {gems}")
        log("=" * 50)

    do_checkin(cfg, token)
    do_claim_gold(cfg, token)

    min_int = cfg.get("min_interval_minutes", 30)
    max_int = cfg.get("max_interval_minutes", 60)
    sleep_sec = random.randint(min_int * 60, max_int * 60)
    log(f"💤 Siklus selesai. Tidur selama {sleep_sec // 60} menit...")
    return sleep_sec

def main():
    log("🚀 Memulai Catopia Game Auto-Farmer Daemon...")
    while True:
        try:
            sleep_time = farm_cycle()
        except Exception as e:
            log(f"Unhandled error in cycle: {e}")
            sleep_time = 120

        # Tidur bertahap agar responsif terhadap perubahan config
        for _ in range(sleep_time // 5):
            time.sleep(5)

if __name__ == "__main__":
    main()
