#!/usr/bin/env python3
"""
Deep Mine (@MineDeepBot) Auto-Farmer Daemon
Mining Real USDT on TON Network
Fitur:
1. Auto-Handshake Sinyal Iklan (ad_start -> ad_done -> activate_miner)
2. Auto-Stack durasi penambangan hingga 4 jam
3. Auto-Claim bonus harian (daily_claim)
4. Logging saldo USDT real-time & sisa durasi penambangan
5. Dynamic config reload & error handling
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
API_BASE = "https://linobot.ir/mine/api.php?v=69"

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

def get_headers(cfg):
    return {
        "Origin": "https://linobot.ir",
        "Referer": "https://linobot.ir/mine/?v=69",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Accept": "application/json, text/plain, */*"
    }

def activate_miner_cycle(init_data, headers):
    log("[DeepMine] Memulai urutan handshake aktivasi penambangan...")
    try:
        # Step 1: ad_start
        requests.post(f"{API_BASE}&action=ad_start", data={"init_data": init_data}, headers=headers, timeout=15)
        time.sleep(2)

        # Step 2: ad_done
        requests.post(f"{API_BASE}&action=ad_done", data={"init_data": init_data}, headers=headers, timeout=15)
        time.sleep(1)

        # Step 3: activate_miner with retry
        for attempt in range(8):
            r = requests.post(f"{API_BASE}&action=activate_miner", data={"init_data": init_data}, headers=headers, timeout=15)
            if r.status_code == 200:
                res = r.json()
                if res.get("ok"):
                    log(">> BERHASIL MENGAKTIFKAN SIKLUS PENAMBANGAN DEEP MINE (+1 JAM)! <<")
                    return True
                if res.get("reason") == "full":
                    log("[DeepMine] Miner sudah penuh (maksimal tumpukan 4 jam).")
                    return True
            requests.post(f"{API_BASE}&action=ad_done", data={"init_data": init_data}, headers=headers, timeout=10)
            time.sleep(1.2)
    except Exception as e:
        log(f"[DeepMine] Error aktivasi: {e}")
    return False

def run_farmer():
    log("==================================================")
    log("       DEEP MINE AUTO-FARMER DAEMON (USDT)        ")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            init_data = cfg.get("init_data", "").strip()
            if not init_data:
                log("init_data kosong! Menunggu auth_generator memperbarui token...")
                time.sleep(30)
                continue

            headers = get_headers(cfg)
            r = requests.post(f"{API_BASE}&action=init", data={"init_data": init_data}, headers=headers, timeout=15)
            if r.status_code != 200:
                log(f"[DeepMine] HTTP Error {r.status_code}: {r.text[:80]}")
                time.sleep(60)
                continue

            data = r.json()
            if not data.get("ok"):
                log(f"[DeepMine] Respon server tidak valid: {data}")
                time.sleep(60)
                continue

            user = data.get("user", {})
            usdt_bal = float(user.get("usdt", 0) or 0)
            miner = user.get("miner", {})
            active = bool(miner.get("active", False))
            end_at = int(miner.get("end_at", 0) or 0)
            now_ts = int(time.time())
            seconds_left = max(0, end_at - now_ts)
            rate_hr = float(miner.get("rate_per_hour", 0.025) or 0.025)
            total_act = int(miner.get("total_activations", 0) or 0)

            # Daily claim
            daily = user.get("daily", {})
            if not daily.get("claimed", False) and daily.get("ads", 0) >= daily.get("goal", 5):
                log("[DeepMine] Target harian tercapai! Mengambil bonus daily_claim...")
                try:
                    r_d = requests.post(f"{API_BASE}&action=daily_claim", data={"init_data": init_data}, headers=headers, timeout=15)
                    if r_d.status_code == 200 and r_d.json().get("ok"):
                        log(f">> KLAIM HARIAN SUKSES: +${r_d.json().get('reward', 0.03)} USDT! <<")
                except Exception as de:
                    log(f"[DeepMine] Error daily claim: {de}")

            log("-" * 50)
            log(f"⛏ [STATUS] Mining: {'AKTIF' if active and seconds_left > 0 else 'BERHENTI'}")
            log(f"💰 Saldo USDT: ${usdt_bal:,.6f} USDT | Hashrate: ${rate_hr:.3f}/jam")
            log(f"⏳ Sisa Waktu: {seconds_left // 60} menit ({seconds_left} detik) | Total Sesi: {total_act}")
            log("-" * 50)

            # Auto activate jika mati atau sisa waktu < 1 jam (stack hingga 4 jam)
            if not active or seconds_left < 3600:
                activate_miner_cycle(init_data, headers)

            # Istirahat adaptif
            sleep_sec = 600 if seconds_left > 1200 else 60
            time.sleep(sleep_sec)

        except Exception as e:
            log(f"[DeepMine] Exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_farmer()
