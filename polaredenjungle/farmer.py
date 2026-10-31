#!/usr/bin/env python3
"""
Polar Eden Jungle (@polaredenjunglebot) Auto-Farmer Daemon
Token: $PEJ on TON Network
Fitur:
1. Auto-login & Bearer token exchange via init_data
2. Auto-start mining jika status idle/expired
3. Auto-claim mined PEJ balance (/api/mining/claim)
4. Tracking saldo & hashrate
"""

import os
import sys
import time
import json
import urllib.parse
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
API_BASE = "https://api.polaredenjungle.top/api"
WEB_ORIGIN = "https://web.polaredenjungle.top"

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
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error membaca config: {e}")
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log(f"Gagal menyimpan config: {e}")

def get_headers(token=None, cfg=None):
    if cfg is None:
        cfg = {}
    h = {
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Referer": f"{WEB_ORIGIN}/",
        "Origin": WEB_ORIGIN,
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }
    if token:
        clean_token = token.replace("Bearer ", "").strip()
        h["Authorization"] = f"Bearer {clean_token}"
    return h

def login_exchange(cfg):
    init_data = cfg.get("init_data", "").strip()
    if not init_data:
        return None
    try:
        qs = urllib.parse.parse_qs(init_data)
        u_raw = qs.get("user", ["{}"])[0]
        u_obj = json.loads(u_raw)
        payload = {
            "tg_id": u_obj.get("id"),
            "name": u_obj.get("first_name", "Local Miner"),
            "photo_url": u_obj.get("photo_url", ""),
            "startapp": "",
            "init_data": init_data
        }
        headers = get_headers(cfg=cfg)
        r = requests.post(f"{API_BASE}/login", json=payload, headers=headers, timeout=15)
        if r.status_code == 200 and r.json().get("code") == 1:
            token = r.json().get("data", {}).get("token", "")
            if token:
                cfg["token"] = token
                save_config(cfg)
                log(">> Berhasil login & menukar init_data menjadi Bearer token PEJ <<")
                return token
        else:
            log(f"[PEJ] Login gagal (HTTP {r.status_code}): {r.text[:100]}")
    except Exception as e:
        log(f"[PEJ] Exception login exchange: {e}")
    return None

def fetch_bootstrap(token, cfg):
    headers = get_headers(token, cfg)
    try:
        r = requests.get(f"{API_BASE}/bootstrap", headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("code") == 1:
                return res.get("data", {})
        elif r.status_code in (401, 403):
            return "EXPIRED"
    except Exception as e:
        log(f"[PEJ] Exception bootstrap: {e}")
    return None

def check_and_claim_mining(token, user_data, cfg):
    mining = user_data.get("mining") or {}
    active = mining.get("active", False)
    pending = float(mining.get("pending", 0) or 0)
    ends_at = int(mining.get("ends_at", 0) or 0)
    now_ts = int(time.time())
    headers = get_headers(token, cfg)

    if not active or (ends_at > 0 and now_ts >= ends_at):
        log("[PEJ] Sesi mining belum aktif atau selesai. Mengirim /api/mining/start...")
        try:
            r_start = requests.post(f"{API_BASE}/mining/start", headers=headers, json={}, timeout=15)
            if r_start.status_code == 200 and r_start.json().get("code") == 1:
                log(">> Berhasil memulai siklus penambangan PEJ baru! <<")
        except Exception as e:
            log(f"[PEJ] Error start: {e}")

    if pending >= 0.1 or (not active and pending > 0):
        log(f"[PEJ] Pending reward: {pending:.4f} PEJ. Mengirim /api/mining/claim...")
        try:
            r_claim = requests.post(f"{API_BASE}/mining/claim", headers=headers, json={}, timeout=15)
            if r_claim.status_code == 200 and r_claim.json().get("code") == 1:
                new_bal = float(r_claim.json().get("data", {}).get("assets", 0) or 0)
                log(f">> KLAIM MINING PEJ SUKSES! Saldo: {new_bal:,.4f} PEJ <<")
                return True
        except Exception as e:
            log(f"[PEJ] Error claim: {e}")
    return False

def run_farmer():
    log("==================================================")
    log("   POLAR EDEN JUNGLE ($PEJ) AUTO-FARMER DAEMON    ")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            token = cfg.get("token", "").strip()
            if not token:
                token = login_exchange(cfg)
                if not token:
                    time.sleep(30)
                    continue

            data = fetch_bootstrap(token, cfg)
            if data == "EXPIRED":
                log("[PEJ] Token expired, mencoba login ulang...")
                token = login_exchange(cfg)
                time.sleep(10)
                continue

            if not data:
                time.sleep(60)
                continue

            user = data.get("user") or {}
            balance = float(user.get("assets", 0) or 0)
            mining = data.get("mining") or {}
            active = bool(mining.get("active", False))
            speed = float(mining.get("speed", 0) or 0)
            pending = float(mining.get("pending", 0) or 0)

            log("-" * 50)
            log(f"⛏ [STATUS] Mining: {'AKTIF' if active else 'IDLE'} | Speed: {speed:.2f} PEJ/jam")
            log(f"💰 Saldo: {balance:,.4f} PEJ | Pending: {pending:.4f} PEJ")
            log("-" * 50)

            check_and_claim_mining(token, data, cfg)
            time.sleep(600)
        except Exception as e:
            log(f"[PEJ] Loop exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_farmer()
