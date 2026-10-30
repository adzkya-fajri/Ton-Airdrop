#!/usr/bin/env python3
"""
Tomarket Telegram Mini-App Auto-Farmer ($TOMA)
Handles:
1. Auto login / session refresh with init_data
2. Daily check-in claim (+3000 points / tickets / stars)
3. 6-Hour Farming Cycle Auto-Claim & Restart
4. Real-time balance and harvest logging
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")

API_BASE = "https://api-web.tomarket.ai/tomarket-game/v1"

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

def login(cfg):
    init_data = cfg.get("init_data", "")
    if not init_data:
        log("init_data kosong! Menunggu disuntik oleh auth_generator...")
        return None

    headers = {
        "Origin": "https://mini-app.tomarket.ai",
        "Referer": "https://mini-app.tomarket.ai/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
        "Content-Type": "application/json"
    }
    payload = {
        "init_data": init_data,
        "invite_code": "",
        "from": "",
        "is_bot": False
    }
    try:
        r = requests.post(f"{API_BASE}/user/login", json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            res_json = r.json()
            if res_json.get("status") == 0:
                token = res_json.get("data", {}).get("access_token")
                if token:
                    cfg["access_token"] = token
                    save_config(cfg)
                    log(f"Login sukses! User: {res_json.get('data', {}).get('fn')} (ID: {res_json.get('data', {}).get('id')})")
                    return token
        log(f"Login gagal: HTTP {r.status_code} - {r.text[:200]}")
    except Exception as e:
        log(f"Exception saat login: {e}")
    return None

def get_headers(cfg, token):
    return {
        "Origin": "https://mini-app.tomarket.ai",
        "Referer": "https://mini-app.tomarket.ai/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
        "Content-Type": "application/json",
        "Authorization": token
    }

def check_daily(cfg, headers):
    daily_game_id = cfg.get("daily_game_id", "fa873d13-d831-4d6f-8aee-9cff7a1d0db1")
    try:
        r = requests.post(f"{API_BASE}/daily/claim", json={"game_id": daily_game_id}, headers=headers, timeout=15)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == 0:
                data = d.get("data", {})
                pts = data.get("today_points", 0)
                counter = data.get("check_counter", 0)
                log(f"🎁 Daily Check-In Sukses! Hari ke-{counter} (+{pts:,.0f} points)")
            elif d.get("status") in (400, 10001) or "already" in d.get("message", "").lower() or "repeat" in d.get("message", "").lower():
                log("Daily check-in sudah diklaim hari ini.")
            else:
                log(f"Status daily check-in: {d.get('message', 'None')}")
    except Exception as e:
        log(f"Error daily check-in: {e}")

def run_farmer():
    log("==================================================")
    log("   TOMARKET ($TOMA) TELEGRAM MINI-APP AUTO-FARM   ")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            token = cfg.get("access_token", "")
            if not token:
                token = login(cfg)
                if not token:
                    time.sleep(30)
                    continue

            headers = get_headers(cfg, token)

            # Check Balance & Farming State
            r = requests.post(f"{API_BASE}/user/balance", json={}, headers=headers, timeout=15)
            if r.status_code in (401, 403) or (r.status_code == 200 and r.json().get("status") in (401, 10002)):
                log("Token expired, me-refresh login...")
                token = login(cfg)
                if not token:
                    time.sleep(30)
                    continue
                headers = get_headers(cfg, token)
                r = requests.post(f"{API_BASE}/user/balance", json={}, headers=headers, timeout=15)

            if r.status_code != 200:
                log(f"Gagal memeriksa balance: HTTP {r.status_code}")
                time.sleep(60)
                continue

            bal_res = r.json()
            if bal_res.get("status") != 0:
                log(f"Response error balance: {bal_res}")
                time.sleep(60)
                continue

            bal_data = bal_res.get("data", {})
            available_balance = bal_data.get("available_balance", 0)
            play_passes = bal_data.get("play_passes", 0)
            farming = bal_data.get("farming") or {}

            # Perform daily claim if needed
            check_daily(cfg, headers)

            game_id = cfg.get("game_id", "53b22103-c7ff-413d-bc63-20f6fb806a07")
            now = int(time.time())

            if not farming:
                log(f"Status Farming: Belum dimulai. Memulai farming baru...")
                s_res = requests.post(f"{API_BASE}/farm/start", json={"game_id": game_id}, headers=headers, timeout=15)
                log(f"Start Farm Response: {s_res.json()}")
                end_at = now + 21600
            else:
                end_at = farming.get("end_at", 0)
                points_accum = farming.get("points", 0)

                if now >= end_at:
                    log(f"🌾 Siklus Farming Selesai! Mengklaim hasil panen...")
                    c_res = requests.post(f"{API_BASE}/farm/claim", json={"game_id": game_id}, headers=headers, timeout=15)
                    c_data = c_res.json()
                    claimed = c_data.get("data", {}).get("claim_this_time", points_accum)
                    log(f"🎉 SUKSES KLAIM FARMING! Hasil: +{claimed} Poin TOMA")

                    # Restart cycle
                    time.sleep(2)
                    s_res = requests.post(f"{API_BASE}/farm/start", json={"game_id": game_id}, headers=headers, timeout=15)
                    s_data = s_res.json()
                    if s_data.get("status") == 0:
                        end_at = s_data.get("data", {}).get("end_at", now + 21600)
                        log(f"🚀 Siklus Farming 6-Jam Baru Berhasil Dimulai! Selesai pada: {datetime.fromtimestamp(end_at).strftime('%H:%M:%S')}")
                    else:
                        end_at = now + 21600
                else:
                    remaining_sec = end_at - now
                    hours = remaining_sec // 3600
                    minutes = (remaining_sec % 3600) // 60
                    seconds = remaining_sec % 60
                    finish_time = datetime.fromtimestamp(end_at).strftime("%d/%m/%Y %H:%M:%S")
                    log(f"🟢 [STATUS] Saldo: {available_balance:,.0f} Poin | Tiket Game: {play_passes}")
                    log(f"⏳ Farming Berjalan: Sisa {hours}j {minutes}m {seconds}s (Selesai pada: {finish_time})")

            # Determine sleep time (check every 10 minutes or wake up at end_at)
            sleep_sec = min(600, max(30, end_at - int(time.time())))
            time.sleep(sleep_sec)

        except Exception as e:
            log(f"Error pada loop utama: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_farmer()
