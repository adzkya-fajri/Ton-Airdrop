#!/usr/bin/env python3
"""
CHICKEN Empire Telegram Mini-App Auto-Farmer
Ekosistem Gram Buddies (@chicken_empirebot)
Fitur:
1. Auto-Auth & Sinkronisasi Data Profil (Power, Hashes, Saldo TON)
2. Auto-Restart Sesi Produksi Bertelur (Siklus 6 Jam)
3. Auto-Claim Hasil Produksi Telur/Hashes & Konversi TON
4. Auto-Spin Mesin Slot Harian (Free Power Booster)
5. Auto-Claim Welcome Bonus jika belum diambil
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
    tid = cfg.get("tid", 1523)
    return {
        "Origin": "https://app.miniempire.app",
        "Referer": f"https://app.miniempire.app/miniapp/index.html?tid={tid}&lang=en",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json"
    }

def run_farmer():
    log("==================================================")
    log("   CHICKEN EMPIRE AUTO-FARMER (GRAM BUDDIES)      ")
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

            tid = cfg.get("tid", 1523)
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
            hashes = user.get("hashes", 0)
            hashes_ton = user.get("hashes_ton", 0)
            balance = user.get("balance", 0)
            prod_ends_at = user.get("hashes_production_ends_at", 0)
            welcome_claimed = user.get("welcome_bonus_claimed", True)

            log(f"🐔 [PROFIL] Power: {power:,} CORN | Telur/Hashes: {hashes:.4f} | Est TON: {hashes_ton:.6f} | Saldo: {balance} TON")

            # 2. Claim Welcome Bonus jika baru
            if not welcome_claimed:
                try:
                    r_wel = requests.post(f"{API_BASE}/claim-welcome-bonus?tid={tid}", json=payload, headers=headers, timeout=15)
                    if r_wel.status_code == 200:
                        w_res = r_wel.json()
                        log(f"🎁 [WELCOME] Klaim bonus pemula sukses: +{w_res.get('power_awarded', 0)} Power!")
                except Exception as we:
                    log(f"Error klaim welcome bonus: {we}")

            # 3. Auto-Claim hasil produksi telur/hashes
            if cfg.get("auto_claim", True):
                try:
                    r_claim = requests.post(f"{API_BASE}/claim?tid={tid}", json=payload, headers=headers, timeout=15)
                    if r_claim.status_code == 200:
                        c_data = r_claim.json()
                        added = c_data.get("hashes_added", 0)
                        tot_h = c_data.get("total_hashes", 0)
                        tot_ton = c_data.get("total_hashes_ton", 0)
                        if added > 0:
                            log(f"🥚 [PANEN] Berhasil panen: +{added:.4f} Hashes | Total: {tot_h:.4f} (≈ {tot_ton:.6f} TON)")
                except Exception as ce:
                    log(f"Error panen telur: {ce}")

            # 4. Auto-Restart Sesi Produksi Bertelur (6 Jam)
            now_ts = int(time.time())
            if cfg.get("auto_production", True) and prod_ends_at <= now_ts:
                try:
                    r_prod = requests.post(f"{API_BASE}/start-production?tid={tid}", json=payload, headers=headers, timeout=15)
                    if r_prod.status_code == 200:
                        p_data = r_prod.json()
                        log(f"🚀 [PRODUKSI] Sesi produksi bertelur dimulai untuk {p_data.get('session_hours', 6)} jam ke depan!")
                except Exception as pe:
                    log(f"Error memulai produksi: {pe}")
            else:
                rem_prod = max(0, prod_ends_at - now_ts)
                log(f"⏳ [STATUS] Sesi bertelur sedang aktif (Sisa: {rem_prod // 3600}j {(rem_prod % 3600) // 60}m)")

            # 5. Auto-Spin Mesin Slot Gratis
            if cfg.get("auto_spin", True) and (next_spin_time <= now_ts):
                try:
                    r_spin = requests.post(f"{API_BASE}/tasks/slot-spin?tid={tid}", json=payload, headers=headers, timeout=15)
                    if r_spin.status_code == 200:
                        s_data = r_spin.json()
                        reels = " ".join(s_data.get("reels", []))
                        pips = s_data.get("pips_awarded", 0)
                        log(f"🎰 [SLOT] Putaran Berhasil! [{reels}] -> Dapat +{pips} Power Booster!")
                        nxt_ts = s_data.get("next_spin_at", 0)
                        if nxt_ts > 0:
                            next_spin_time = int(nxt_ts / 1000)
                    else:
                        # Cooldown
                        next_spin_time = now_ts + 3600
                except Exception as se:
                    log(f"Error memutar slot: {se}")

            # Interval sleep
            interval = cfg.get("check_interval_seconds", 600)
            log(f"💤 Siklus selesai. Tidur {interval // 60} menit sebelum siklus panen berikutnya...\n")
            time.sleep(interval)

        except Exception as e:
            log(f"Error pada loop utama Chicken Empire: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_farmer()
