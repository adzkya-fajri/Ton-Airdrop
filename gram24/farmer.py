#!/usr/bin/env python3
"""
GRAM24 Mining (@Gram24MiningBot) Telegram Mini-App Auto-Farmer
MiniEmpire Engine (tid=2176)
Fitur:
1. Auto-Auth & Sinkronisasi Profil (Power, Hashes, Saldo Gram/TON/USDT)
2. Auto-Restart Sesi Produksi Tambang GPU
3. Auto-Claim Hasil Produksi Mining
4. Auto-Claim Welcome Bonus jika tersedia
5. Auto-Spin Mesin Lucky jika tersedia
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
API_BASE = "https://app.miniempire.app/miniapp"

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
    tid = cfg.get("tid", 2176)
    return {
        "Origin": "https://app.miniempire.app",
        "Referer": f"https://app.miniempire.app/miniapp/index.html?tid={tid}&lang=en",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json"
    }

def run_farmer():
    log("==================================================")
    log("     GRAM24 MINING AUTO-FARMER (MINIEMPIRE)       ")
    log("==================================================")

    next_spin_time = 0

    while True:
        try:
            cfg = load_config()
            init_data = cfg.get("init_data", "")
            if not init_data:
                log("init_data kosong! Menunggu auto_generator menginjeksi token...")
                time.sleep(30)
                continue

            tid = cfg.get("tid", 2176)
            headers = get_headers(cfg)
            payload = {"initData": init_data}

            # 1. Auth & Get Profile Status
            r_auth = requests.post(f"{API_BASE}/auth?tid={tid}", json=payload, headers=headers, timeout=15)
            if r_auth.status_code != 200:
                log(f"Gagal otentikasi profil (HTTP {r_auth.status_code}): {r_auth.text[:120]}")
                time.sleep(60)
                continue

            data = r_auth.json()
            user = data.get("user", {})
            power = user.get("power", 0)
            hashes = float(user.get("hashes", 0) or 0)
            hashes_ton = float(user.get("hashes_ton", 0) or 0)
            balance = float(user.get("balance", 0) or 0)
            prod_ends_at = int(user.get("hashes_production_ends_at", 0) or 0)
            welcome_claimed = bool(user.get("welcome_bonus_claimed", True))

            log(f"💎 [PROFIL] Hashrate Power: {power:,} | Mined Hashes: {hashes:.4f} | Est Nilai: {hashes_ton:.6f} | Saldo: {balance}")

            # 2. Claim Welcome Bonus jika belum diambil
            if not welcome_claimed:
                try:
                    r_wel = requests.post(f"{API_BASE}/claim-welcome-bonus?tid={tid}", json=payload, headers=headers, timeout=15)
                    if r_wel.status_code == 200:
                        w_res = r_wel.json()
                        log(f"🎁 [WELCOME] Klaim bonus pemula sukses: +{w_res.get('power_awarded', 0)} Power!")
                except Exception as we:
                    log(f"Error klaim welcome bonus: {we}")

            # 3. Auto-Claim hasil produksi
            if cfg.get("auto_claim", True):
                now_ts = int(time.time())
                if hashes > 0 and (now_ts >= prod_ends_at or hashes >= 10.0):
                    try:
                        r_claim = requests.post(f"{API_BASE}/claim-hashes?tid={tid}", json=payload, headers=headers, timeout=15)
                        if r_claim.status_code == 200:
                            c_res = r_claim.json()
                            new_b = c_res.get("new_balance", balance)
                            log(f"💰 [KLAIM] Klaim hashes sukses! Saldo sekarang: {new_b}")
                    except Exception as ce:
                        log(f"Error claim hashes: {ce}")

            # 4. Auto-Restart sesi produksi jika mati
            now_ts = int(time.time())
            if now_ts >= prod_ends_at:
                try:
                    log("⚡ Menyalakan kembali siklus penambangan GPU...")
                    r_start = requests.post(f"{API_BASE}/restart-hashes-production?tid={tid}", json=payload, headers=headers, timeout=15)
                    if r_start.status_code == 200:
                        s_res = r_start.json()
                        new_ends = s_res.get("user", {}).get("hashes_production_ends_at", 0)
                        log(f"✅ Sesi penambangan berhasil dimulai ulang! Aktif sampai: {datetime.fromtimestamp(new_ends).strftime('%H:%M:%S')}")
                except Exception as se:
                    log(f"Error restart production: {se}")

            # 5. Auto-Spin jika slot tersedia
            if now_ts >= next_spin_time:
                try:
                    r_spin = requests.post(f"{API_BASE}/spin-fortune-wheel?tid={tid}", json=payload, headers=headers, timeout=15)
                    if r_spin.status_code == 200:
                        sp_res = r_spin.json()
                        if sp_res.get("success"):
                            log(f"🎰 [LUCKY] Spin berhasil! Hadiah: {sp_res.get('prize', 'Bonus Power')}")
                            next_spin_time = now_ts + (sp_res.get("cooldown", 3600))
                        else:
                            next_spin_time = now_ts + 1800
                    else:
                        next_spin_time = now_ts + 1800
                except Exception as spe:
                    log(f"Error spin fortune wheel: {spe}")
                    next_spin_time = now_ts + 1800

            time.sleep(300)

        except Exception as e:
            log(f"Exception di main loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_farmer()
