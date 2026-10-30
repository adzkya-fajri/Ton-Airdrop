#!/usr/bin/env python3
"""
Clayton Game Telegram Mini-App Auto-Farmer ($CLAY)
Features:
1. Dynamic config reload & integration with auth-generator
2. Exchange Init-Data header for user authorization (/api/user/authorization)
3. Auto daily login reward (/api/user/daily-claim)
4. Auto daily tasks reward claim (/api/tasks/claim)
5. Real-time balance and ticket logging
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
BASE_URL = "https://tonclayton.fun"

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

def get_headers(cfg):
    init_data = cfg.get("init_data", "")
    return {
        "Host": "tonclayton.fun",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "Init-Data": init_data,
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }

def login(cfg):
    init_data = cfg.get("init_data", "")
    if not init_data:
        log("init_data kosong! Menunggu penyegaran token oleh auth_generator...")
        return None
    url = f"{BASE_URL}/api/user/authorization"
    headers = get_headers(cfg)
    try:
        res = requests.post(url, headers=headers, json={}, timeout=15)
        if res.status_code in [200, 201]:
            data = res.json()
            user = data.get("user", {})
            name = user.get("username") or user.get("first_name") or "Player"
            points = user.get("tokens") or user.get("points") or 0
            tickets = user.get("game_tickets") or user.get("tickets") or 0
            daily = data.get("dailyReward", {})

            log("=" * 50)
            log(f"🌱 [Clayton] Akun: {name} | 🪙 Saldo CLAY: {points} | 🎟️ Tiket: {tickets}")
            log("=" * 50)
            return data
        log(f">> Login gagal: HTTP {res.status_code} - {res.text[:100]} <<")
    except Exception as e:
        log(f">> Exception saat login: {e} <<")
    return None

def do_daily_claim(cfg, login_data):
    if not cfg.get("auto_daily_claim", True) or not login_data:
        return
    daily = login_data.get("dailyReward", {})
    if daily.get("can_claim_today"):
        url = f"{BASE_URL}/api/user/daily-claim"
        headers = get_headers(cfg)
        try:
            res = requests.post(url, headers=headers, json={}, timeout=15)
            if res.status_code in [200, 201]:
                log("🎉 Daily Reward Clayton Berhasil Diklaim!")
        except Exception as e:
            log(f">> Gagal klaim daily: {e} <<")

def farm_cycle():
    cfg = load_config()
    login_data = login(cfg)
    if not login_data:
        return 120

    do_daily_claim(cfg, login_data)

    min_int = cfg.get("min_interval_minutes", 60)
    max_int = cfg.get("max_interval_minutes", 120)
    sleep_sec = random.randint(min_int * 60, max_int * 60)
    log(f"💤 Siklus Clayton selesai. Tidur selama {sleep_sec // 60} menit...")
    return sleep_sec

def main():
    log("🚀 Memulai Clayton Game Auto-Farmer Daemon...")
    while True:
        try:
            sleep_time = farm_cycle()
        except Exception as e:
            log(f"Unhandled error in cycle: {e}")
            sleep_time = 120

        # Tidur bertahap agar responsif terhadap pembaruan token
        for _ in range(sleep_time // 5):
            time.sleep(5)

if __name__ == "__main__":
    main()
