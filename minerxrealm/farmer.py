#!/usr/bin/env python3
"""
MinerXRealm Telegram Mini-App Auto-Farmer
Mendukung penambangan koin & $GRAM (TON) otomatis:
1. Auto-Start Sesi Mining (Siklus 1 Jam, maks 5 siklus per hari)
2. Auto-Claim Hasil Mining (/api/mine/claim)
3. Auto-Claim Daily Chest (/api/chest/claim)
4. Auto-Claim Daily Wheel Spin (/api/spin/claim)
5. Auto-Claim Pick a Gift (/api/giftpick/claim)
6. Auto-Roll Daily Dice (/api/dice/claim)
"""

import os
import sys
import time
import json
import uuid
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
API_BASE = "https://minerxrealm.zekobusiness0.workers.dev/api"

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
    return {
        "Origin": "https://minerxrealm.zekobusiness0.workers.dev",
        "Referer": "https://minerxrealm.zekobusiness0.workers.dev/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json"
    }

def run_farmer():
    log("==================================================")
    log("   MINERXREALM AUTO-FARMER (COINS & GRAM/TON)     ")
    log("==================================================")

    device_id = str(uuid.uuid4())
    last_daily_claim_date = ""

    while True:
        try:
            cfg = load_config()
            init_data = cfg.get("init_data", "")
            if not init_data:
                log("init_data kosong! Menunggu auto_generator menginjeksi token...")
                time.sleep(30)
                continue

            headers = get_headers(cfg)
            payload = {"initData": init_data}

            # 1. Fetch User Data
            r_user = requests.post(f"{API_BASE}/user", json={"initData": init_data, "device_id": device_id}, headers=headers, timeout=15)
            if r_user.status_code != 200:
                log(f"Gagal memuat status user (HTTP {r_user.status_code}): {r_user.text[:120]}")
                time.sleep(60)
                continue

            u_data = r_user.json().get("user", {})
            coins = u_data.get("coins", 0)
            gram = u_data.get("gram", 0)
            mining_started = u_data.get("mining_started_at")
            cycles_today = u_data.get("mining_cycles_today", 0)
            cycles_max = u_data.get("mining_cycles_max", 5)
            duration_sec = u_data.get("mining_cycle_duration_seconds", 3600)

            log(f"⛏️ [PROFIL] Saldo: {coins:,} Koin | {gram:.4f} GRAM (TON) | Siklus Hari Ini: {cycles_today}/{cycles_max}")

            now_ts = time.time()

            # 2. Daily Rewards (Chest, Spin, Giftpick, Dice)
            today_str = datetime.now().strftime("%Y-%m-%d")
            if cfg.get("auto_daily_claims", True) and last_daily_claim_date != today_str:
                daily_endpoints = [
                    ("Daily Chest", "/chest/claim"),
                    ("Lucky Spin", "/spin/claim"),
                    ("Pick a Gift", "/giftpick/claim"),
                    ("Lucky Dice", "/dice/claim"),
                ]
                for name, ep in daily_endpoints:
                    try:
                        r_d = requests.post(f"{API_BASE}{ep}", json=payload, headers=headers, timeout=10)
                        if r_d.status_code == 200:
                            res = r_d.json()
                            p_type = res.get("prize_type", "reward")
                            p_amt = res.get("prize_amount", 0)
                            log(f"🎁 [{name}] Klaim sukses: +{p_amt} {p_type}!")
                    except Exception as de:
                        log(f"Error {name}: {de}")
                last_daily_claim_date = today_str

            # 3. Handle Mining Cycles
            if cfg.get("auto_mine", True):
                if not mining_started:
                    if cycles_today < cycles_max:
                        try:
                            r_start = requests.post(f"{API_BASE}/mine/start", json=payload, headers=headers, timeout=15)
                            if r_start.status_code == 200:
                                log(f"🚀 [MINING] Siklus penambangan #{cycles_today + 1} dimulai! Durasi: {duration_sec // 60} menit.")
                        except Exception as se:
                            log(f"Error start mining: {se}")
                    else:
                        log(f"💤 [MINING] Batas harian tercapai ({cycles_today}/{cycles_max} siklus). Menunggu reset harian.")
                else:
                    # Parse start time
                    try:
                        # e.g. "2026-10-27T13:48:23.406Z"
                        cleaned_ts = mining_started.replace("Z", "+00:00")
                        start_dt = datetime.fromisoformat(cleaned_ts).timestamp()
                        elapsed = now_ts - start_dt
                        if elapsed >= duration_sec:
                            r_claim = requests.post(f"{API_BASE}/mine/claim", json=payload, headers=headers, timeout=15)
                            if r_claim.status_code == 200:
                                c_res = r_claim.json()
                                log(f"✅ [MINING] Siklus penambangan selesai! Hadiah diklaim.")
                                # Langsung mulai siklus berikutnya jika slot masih ada
                                if cycles_today + 1 < cycles_max:
                                    requests.post(f"{API_BASE}/mine/start", json=payload, headers=headers, timeout=15)
                                    log(f"🚀 [MINING] Melanjutkan siklus #{cycles_today + 2}...")
                            else:
                                log(f"⚠️ [MINING] Gagal klaim: {r_claim.text[:100]}")
                        else:
                            rem = int(duration_sec - elapsed)
                            log(f"⏳ [MINING] Sedang menambang (Sisa waktu: {rem // 60}m {rem % 60}s)")
                    except Exception as te:
                        log(f"Error evaluasi timer mining: {te}")

            # Interval sleep
            interval = cfg.get("check_interval_seconds", 600)
            log(f"💤 Siklus selesai. Tidur {interval // 60} menit sebelum pemeriksaan berikutnya...\n")
            time.sleep(interval)

        except Exception as e:
            log(f"Error pada loop utama MinerXRealm: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_farmer()
