#!/usr/bin/env python3
"""
Music Mining ($MB) Telegram Mini-App Auto-Farmer
Automates:
1. Auto-claim and restart mining cycle (8-hour period)
2. Auto-activation of 3 ad boosts (Gigapub, LibTL, Telegain) for 2.5x hashrate
3. Auto-completion of partner link tasks
4. Real-time logging & graceful error handling
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")

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
        log(f"Config file not found: {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def get_headers(cfg):
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['token']}",
        "Origin": "https://musicmb.site",
        "Referer": "https://musicmb.site/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36")
    }

def fetch_dashboard(cfg):
    url = f"{cfg['api_base']}/dashboard"
    try:
        r = requests.get(url, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            return r.json()
        log(f"Failed to fetch dashboard (HTTP {r.status_code}): {r.text[:200]}")
    except Exception as e:
        log(f"Error fetching dashboard: {e}")
    return None

def start_mining(cfg):
    url = f"{cfg['api_base']}/mining/start"
    try:
        r = requests.post(url, headers=get_headers(cfg), json={}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            log(">> SUKSES START/KLAIM MINING MUSIC MB! <<")
            return data
        log(f"Gagal start mining (HTTP {r.status_code}): {r.text[:200]}")
    except Exception as e:
        log(f"Error starting mining: {e}")
    return None

def claim_mining(cfg, destination="mining"):
    url = f"{cfg['api_base']}/mining/claim"
    try:
        r = requests.post(url, headers=get_headers(cfg), json={"destination": destination}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            earned = float(data.get("earned", 0))
            log(f">> KLAIM BERHASIL! <<")
            log(f"Reward Diklaim : +{earned:.4f} MB (Tujuan: {destination})")
            return data
        log(f"Gagal klaim mining (HTTP {r.status_code}): {r.text[:200]}")
    except Exception as e:
        log(f"Error claiming mining: {e}")
    return None

def ensure_ad_boost(cfg, provider_name, boost_data):
    if not cfg.get("auto_boost", True):
        return

    if not boost_data or boost_data.get("active"):
        return

    endpoint_map = {
        "gigapub": "/mining/ad-boost/complete",
        "libtl": "/mining/libtl-ad-boost/complete",
        "telegain": "/mining/telegain-ad-boost/complete"
    }

    endpoint = endpoint_map.get(provider_name)
    if not endpoint:
        return

    url = f"{cfg['api_base']}{endpoint}"
    ads_remaining = boost_data.get("ads_remaining", 10)
    log(f"Mengaktifkan boost [{provider_name}] ({ads_remaining} iklan tersisa)...")

    for i in range(ads_remaining):
        time.sleep(3.2)
        try:
            r = requests.post(url, headers=get_headers(cfg), json={}, timeout=15)
            if r.status_code == 200:
                res = r.json().get("ad_boost", {})
                watched = res.get("ads_watched", 0)
                is_active = res.get("active", False)
                if is_active:
                    log(f"✅ Boost [{provider_name}] AKTIF! Hashrate: {res.get('boosted_hashrate', 0)} (Durasi: {res.get('duration_hours', 8)} jam)")
                    break
                else:
                    log(f"Boost [{provider_name}] progres: {watched}/10")
            elif r.status_code == 422:
                time.sleep(2.5)
            else:
                log(f"Boost [{provider_name}] gagal (HTTP {r.status_code}): {r.text[:150]}")
        except Exception as e:
            log(f"Error activating boost [{provider_name}]: {e}")

def complete_link_tasks(cfg, tasks):
    for t in tasks:
        if not t.get("completed") and t.get("verification_type") == "link":
            tid = t.get("id")
            title = t.get("title")
            reward = t.get("reward", 0)
            url = f"{cfg['api_base']}/tasks/{tid}/complete"
            try:
                r = requests.post(url, headers=get_headers(cfg), json={}, timeout=15)
                if r.status_code == 200:
                    log(f"🎉 Sukses menyelesaikan task #{tid} '{title}' -> +{reward} MB!")
                time.sleep(1.5)
            except Exception as e:
                log(f"Error completing task #{tid}: {e}")

def run_loop():
    log("=== Music Mining ($MB) Auto-Farmer Started ===")
    
    while True:
        try:
            cfg = load_config()
            dashboard = fetch_dashboard(cfg)

            if not dashboard:
                retry_sleep = 60
                log(f"⚠️ Gagal mengambil data dashboard (Token expired/perlu verifikasi). Menunggu token baru (/settoken_mb) - cek ulang dalam {retry_sleep} detik...")
                last_mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
                slept = 0
                while slept < retry_sleep:
                    time.sleep(2)
                    slept += 2
                    try:
                        curr_mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
                        if curr_mtime != last_mtime:
                            log("⚡ Perubahan config.json / token MusicMB terdeteksi! Membangunkan farmer segera...")
                            break
                    except Exception:
                        pass
                continue

            user = dashboard.get("user", {})
            mining = dashboard.get("mining", {})
            market = dashboard.get("market", {})
            tasks = dashboard.get("tasks", [])

            bal = float(user.get("balance", 0))
            withdrawable = float(user.get("withdrawable_balance", 0))
            hashrate = float(mining.get("hashrate", 0))
            speed_hr = float(mining.get("speed_per_hour", 0))
            daily_rate = speed_hr * 24.0
            is_active = mining.get("active", False)
            rem_sec = int(mining.get("remaining_seconds", 0))
            usd_price = float(market.get("usd_price", 0))
            next_claim_time = datetime.fromtimestamp(time.time() + rem_sec).strftime("%H:%M:%S")

            log("==================================================")
            log(f"User          : {user.get('name')} (@{user.get('username')})")
            log(f"Total Saldo   : {bal:.4f} MB")
            log(f"Withdrawable  : {withdrawable:.4f} MB")
            log(f"Mining Rate   : +{daily_rate:.2f} MB/hari (+{speed_hr:.4f} MB/jam)")
            log(f"Hashrate      : {hashrate:.2f} GH/s")
            log(f"Mining Active : {is_active}")
            log(f"Klaim berikutnya: {next_claim_time}")
            log(f"Sisa Waktu    : {rem_sec} detik (~{rem_sec // 60} menit)")
            log("==================================================")

            # 1. Complete uncompleted link tasks
            complete_link_tasks(cfg, tasks)

            # 2. Check and activate boosts
            ensure_ad_boost(cfg, "gigapub", dashboard.get("ad_boost"))
            ensure_ad_boost(cfg, "libtl", dashboard.get("libtl_ad_boost"))
            ensure_ad_boost(cfg, "telegain", dashboard.get("telegain_ad_boost"))

            # 3. Check if mining is expired or inactive
            if not is_active or rem_sec <= 10:
                log("Siklus mining selesai atau belum aktif. Menjalankan start/claim...")
                dest = cfg.get("claim_destination", "mining")
                claim_res = claim_mining(cfg, destination=dest)
                if not claim_res:
                    start_mining(cfg)
                
                time.sleep(5)
                new_dash = fetch_dashboard(cfg)
                if new_dash:
                    rem_sec = int(new_dash.get("mining", {}).get("remaining_seconds", 28800))

            interval = cfg.get("check_interval_seconds", 600)
            sleep_duration = max(30, min(interval, rem_sec))
            log(f"Tidur selama {sleep_duration} detik (~{sleep_duration // 60} menit)...")
            time.sleep(sleep_duration)

        except KeyboardInterrupt:
            log("Farmer dihentikan oleh pengguna.")
            break
        except Exception as e:
            log(f"Unexpected error in farmer loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_loop()
