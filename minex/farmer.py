#!/usr/bin/env python3
"""
MineX (@MineXton_bot) Auto-Farmer Daemon
Platform: https://delist.app/
Automasi:
1. Auto-collect pending mining reward (nTON / NanoTON) via /api/stable/collect-all
2. Auto-claim waiting random claims via /api/user/claims/all
3. Saldo monitoring (nTON di /api/balances2 & MY balance)
4. Dynamic config reload & adaptive backoff
"""

import os
import sys
import time
import json
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
API_BASE = "https://delist.app/api"

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
        log(f"ERROR: File {CONFIG_FILE} tidak ditemukan!")
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error membaca config: {e}")
        return {}

def get_headers(cfg):
    raw_token = cfg.get("init_data") or cfg.get("token") or ""
    raw_token = raw_token.strip().replace("Bearer ", "")
    return {
        "Authorization": f"Bearer {raw_token}",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Referer": "https://delist.app/",
        "Origin": "https://delist.app",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }

def fetch_user(headers):
    try:
        r = requests.get(f"{API_BASE}/user", headers=headers, timeout=12)
        if r.status_code == 200:
            return r.json()
        elif r.status_code in (401, 403):
            log(f">> Token MineX Expired (HTTP {r.status_code})! Perlu Update Token / initData <<")
            return None
        else:
            log(f"[MineX] Gagal fetch user (HTTP {r.status_code}): {r.text[:80]}")
            return None
    except Exception as e:
        log(f"[MineX] Exception fetch user: {e}")
        return None

def fetch_nton_balance(headers):
    try:
        r = requests.get(f"{API_BASE}/balances2", headers=headers, timeout=12)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                for item in data:
                    if item.get("tokenName") == "nTON":
                        return float(item.get("amount", 0) or 0)
        return 0.0
    except Exception as e:
        log(f"[MineX] Exception fetch balances2: {e}")
        return 0.0

def collect_pending_mining(headers):
    try:
        r_pending = requests.get(f"{API_BASE}/stable/collect/pending", headers=headers, timeout=12)
        if r_pending.status_code != 200:
            return 0.0
        p_data = r_pending.json()
        total_pending = float(p_data.get("total", 0) or 0)
        count = int(p_data.get("count", 0) or 0)

        if total_pending > 0 or count > 0:
            log(f"[MineX] Terdeteksi pending mining reward: {total_pending} nTON. Mengirim request /api/stable/collect-all...")
            r_collect = requests.post(f"{API_BASE}/stable/collect-all", headers=headers, json={}, timeout=15)
            if r_collect.status_code == 200:
                res_data = r_collect.json()
                claimed = float(res_data.get("totalCollected") or total_pending or 0)
                log("=" * 50)
                log(f">> KLAIM MINING MINEX BERHASIL! +{claimed:,.2f} nTON <<")
                log("=" * 50)
                return claimed
            else:
                log(f"[MineX] Gagal collect-all (HTTP {r_collect.status_code}): {r_collect.text[:80]}")
        return 0.0
    except Exception as e:
        log(f"[MineX] Exception collect pending: {e}")
        return 0.0

def claim_waiting_claims(headers):
    try:
        r_wait = requests.get(f"{API_BASE}/user/claims/waiting", headers=headers, timeout=12)
        if r_wait.status_code == 200:
            w_data = r_wait.json()
            cnt = int(w_data.get("count", 0) or 0)
            if cnt > 0:
                log(f"[MineX] Terdeteksi {cnt} random claims waiting. Mengirim claim...")
                r_c = requests.post(f"{API_BASE}/user/claims/all", headers=headers, json={}, timeout=15)
                if r_c.status_code == 200:
                    log(f">> Berhasil klaim {cnt} random reward MineX! <<")
    except Exception as e:
        log(f"[MineX] Exception claim waiting: {e}")

def run_loop():
    log("=== MineX Auto-Farmer Daemon Dimulai ===")
    
    while True:
        try:
            cfg = load_config()
            headers = get_headers(cfg)
            raw_token = cfg.get("init_data") or cfg.get("token") or ""

            if not raw_token.strip():
                log("Token/initData MineX kosong di config.json. Menunggu auth generator...")
                time.sleep(15)
                continue

            user_data = fetch_user(headers)
            if not user_data:
                time.sleep(20)
                continue

            username = user_data.get("username", "Zelx_arthur")
            uid = user_data.get("userid", "")

            # 1. Collect pending mining rewards
            collect_pending_mining(headers)

            # 2. Claim waiting random claims
            claim_waiting_claims(headers)

            # 3. Ambil saldo nTON terbaru
            nton_bal = fetch_nton_balance(headers)
            log(f"[MineX] Status: Normal | Akun: @{username} ({uid}) | Saldo: {nton_bal:,.4f} nTON")

        except Exception as e:
            log(f"[MineX] Loop Error: {e}")

        # Sleep interval (60 detik)
        time.sleep(60)

if __name__ == "__main__":
    run_loop()
