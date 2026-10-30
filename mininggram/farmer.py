#!/usr/bin/env python3
"""
Mining GRAM ⛏️ (@MiningGRAM_Bot) Telegram Mini-App Auto-Farmer
Automates:
1. Daily Check-in / Streak claim (/api/checkin)
2. Auto-claim completed miners (/api/miners/claim)
3. Auto-reactivate available miners (/api/miners/activate)
4. Auto-claim trickle rewards (/api/mine/trickle-claim)
5. Real-time balance & dust wallet monitoring (/api/dust-wallet)
6. Adaptive sleep & dynamic token refresh
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
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

def authenticate(cfg):
    """Refreshes session_token using init_data"""
    init_data = cfg.get("init_data", "").strip()
    if not init_data:
        log("init_data belum terisi di config.json!")
        return None

    api_base = cfg.get("api_base", "https://mining-gram-worker.muhaisin0888.workers.dev")
    url = f"{api_base}/api/auth"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://mining-gram-miniapp.pages.dev",
        "Referer": "https://mining-gram-miniapp.pages.dev/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K)")
    }
    try:
        r = requests.post(url, json={"initData": init_data}, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            session_token = data.get("sessionToken")
            if session_token:
                cfg["session_token"] = session_token
                save_config(cfg)
                log(">> Authentikasi Mining GRAM berhasil! Session token tersimpan. <<")
                return session_token
        log(f"Autentikasi gagal (HTTP {r.status_code}): {r.text[:200]}")
    except Exception as e:
        log(f"Error auth Mining GRAM: {e}")
    return None

def get_headers(cfg):
    token = cfg.get("session_token", "").strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "https://mining-gram-miniapp.pages.dev",
        "Referer": "https://mining-gram-miniapp.pages.dev/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K)")
    }

def call_api(cfg, endpoint, method="GET", payload=None):
    api_base = cfg.get("api_base", "https://mining-gram-worker.muhaisin0888.workers.dev")
    url = f"{api_base}{endpoint}"
    headers = get_headers(cfg)
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        else:
            r = requests.post(url, headers=headers, json=payload or {}, timeout=15)

        if r.status_code == 401:
            log("Session token expired, mencoba re-autentikasi...")
            new_token = authenticate(cfg)
            if new_token:
                headers = get_headers(cfg)
                if method == "GET":
                    r = requests.get(url, headers=headers, timeout=15)
                else:
                    r = requests.post(url, headers=headers, json=payload or {}, timeout=15)
        return r
    except Exception as e:
        log(f"Request error pada {endpoint}: {e}")
        return None

def process_checkin(cfg):
    if not cfg.get("auto_checkin", True):
        return
    r = call_api(cfg, "/api/checkin/status")
    if r and r.status_code == 200:
        data = r.json()
        already = data.get("alreadyCheckedInToday", False)
        streak = data.get("streak", 0)
        reward = data.get("rewardDust", "0")
        if not already:
            log(f"Check-in harian tersedia! Mengklaim reward (Hari streak: {streak + 1})...")
            rc = call_api(cfg, "/api/checkin", method="POST")
            if rc and rc.status_code == 200:
                log(f">> CHECK-IN SUKSES! Reward: +{reward} DUST <<")
            else:
                log(f">> Check-in gagal: {rc.status_code if rc else 'No response'} - {rc.text if rc else ''} <<")
        else:
            log(f"Daily check-in sudah diklaim hari ini (Streak: {streak} hari).")

def process_trickle(cfg):
    if not cfg.get("auto_trickle", True):
        return
    r = call_api(cfg, "/api/mine/trickle-status")
    if r and r.status_code == 200:
        data = r.json()
        trickles = data.get("trickles", [])
        for tr in trickles:
            tid = tr.get("id")
            if tid and tr.get("claimable", False):
                log(f"Klaim trickle reward {tid}...")
                rc = call_api(cfg, "/api/mine/trickle-claim", method="POST", payload={"trickleId": tid})
                if rc and rc.status_code == 200:
                    log(f">> Trickle {tid} berhasil diklaim! <<")

def process_miners(cfg):
    r = call_api(cfg, "/api/miners")
    if not r or r.status_code != 200:
        log(f"Gagal mengambil data miners: {r.status_code if r else 'None'}")
        return 300

    data = r.json()
    owned = data.get("owned", [])
    active_count = data.get("activeCount", 0)
    now_utc = datetime.now(timezone.utc)
    
    min_time_left = 3600

    log(f"=== Status Miners ({active_count} Aktif, Total Milik: {len(owned)}) ===")
    
    for miner in owned:
        m_id = miner.get("id")
        m_type = miner.get("miner_type_id", "miner")
        status = miner.get("status")
        finishes_str = miner.get("finishes_at")
        yield_dust = miner.get("yield_dust", 0)

        if status == "active" and finishes_str:
            try:
                # Parse finish time
                dt_str = finishes_str.replace("Z", "+00:00")
                fin_dt = datetime.fromisoformat(dt_str)
                secs_left = int((fin_dt - now_utc).total_seconds())

                if secs_left <= 0:
                    log(f"⛏️ Miner [{m_type}] ({m_id[:8]}) telah selesai! Menjalankan klaim reward (+{yield_dust} DUST)...")
                    if cfg.get("auto_claim_miners", True):
                        rc = call_api(cfg, "/api/miners/claim", method="POST", payload={"minerId": m_id})
                        if rc and rc.status_code == 200:
                            log(f">> KLAIM MINER [{m_type}] SUKSES! +{yield_dust} DUST <<")
                            status = "claimed"
                        else:
                            log(f"Gagal klaim miner: {rc.text if rc else 'No response'}")
                else:
                    hrs = secs_left // 3600
                    mins = (secs_left % 3600) // 60
                    log(f"⛏️ Miner [{m_type}]: Berjalan aktif. Sisa waktu: {hrs}j {mins}m ({secs_left}d)")
                    if secs_left < min_time_left:
                        min_time_left = secs_left
            except Exception as ex:
                log(f"Error parsing date miner {m_id}: {ex}")

        # Auto activate jika miner baru dibeli atau masih di inventory
        if status in ["inventory", "purchased", "inactive"] and cfg.get("auto_activate_miners", True):
            log(f"Mengaktifkan miner [{m_type}] ({m_id[:8]})...")
            ra = call_api(cfg, "/api/miners/activate", method="POST", payload={"minerId": m_id})
            if ra and ra.status_code == 200:
                log(f">> AKTIVASI MINER [{m_type}] SUKSES! <<")
            else:
                log(f"Status aktivasi miner [{m_type}]: {ra.status_code if ra else 'None'} {ra.text[:100] if ra else ''}")

    return max(60, min(min_time_left, 1800))

def fetch_wallet_status(cfg):
    r = call_api(cfg, "/api/dust-wallet")
    if r and r.status_code == 200:
        data = r.json()
        dust_bal = data.get("dustBalance", 0)
        gram_nano = int(data.get("withdrawableGramNanoton", 0))
        gram_bal = gram_nano / 1_000_000_000.0
        ton_price = data.get("tonUsdPrice", 0)
        log("==================================================")
        log(f"Saldo DUST     : {dust_bal:,} DUST")
        log(f"Saldo GRAM     : {gram_bal:.6f} GRAM / TON (USD: ${ton_price})")
        log("==================================================")
        return dust_bal, gram_bal
    return 0, 0.0

def run_loop():
    log("=== Mining GRAM ⛏️ (@MiningGRAM_Bot) Auto-Farmer Started ===")
    
    while True:
        try:
            cfg = load_config()
            if not cfg.get("session_token"):
                token = authenticate(cfg)
                if not token:
                    log("Menunggu ketersediaan init_data dari generator... Tidur 30 detik.")
                    time.sleep(30)
                    continue

            # 1. Tampilkan saldo dompet
            fetch_wallet_status(cfg)

            # 2. Daily Check-in
            process_checkin(cfg)

            # 3. Trickle claims
            process_trickle(cfg)

            # 4. Miner cycle
            next_miner_check = process_miners(cfg)

            interval = cfg.get("check_interval_seconds", 300)
            sleep_duration = min(interval, next_miner_check)
            log(f"Siklus selesai. Tidur selama {sleep_duration} detik (~{sleep_duration // 60} menit)...")
            
            # Adaptive sleep
            last_mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
            slept = 0
            while slept < sleep_duration:
                step = min(5, sleep_duration - slept)
                time.sleep(step)
                slept += step
                try:
                    curr_mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
                    if curr_mtime != last_mtime:
                        log("⚡ Perubahan config.json Mining GRAM terdeteksi! Membangunkan farmer segera...")
                        break
                except Exception:
                    pass

        except KeyboardInterrupt:
            log("Mining GRAM Farmer dihentikan.")
            break
        except Exception as e:
            log(f"Unexpected error in loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_loop()
