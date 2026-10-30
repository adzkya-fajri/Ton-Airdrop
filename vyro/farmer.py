#!/usr/bin/env python3
"""
VYRO Telegram Mini-App Auto-Farmer ($VYRO)
Automates:
1. Dynamic app-session token acquisition from /api/bootstrap
2. Auto-claiming mining rewards at regular intervals (default 30 mins)
3. Preventing 7-hour inactivity pause to keep mining 24/7 continuous
4. Real-time balance and mining metrics tracking
"""

import os
import sys
import time
import json
import uuid
from datetime import datetime, timezone, timedelta
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

def create_session(cfg):
    s = requests.Session()
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://vyro.run.place",
        "Referer": "https://vyro.run.place/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"),
        "Authorization": cfg["auth"],
        "x-vyro-dex": "1",
        "x-vyro-market-balances": "2",
        "x-vyro-mining-bonus": "1",
        "x-vyro-ui-contract": "claim-inactivity-v1",
        "x-vyro-expeditions": "1",
        "x-vyro-vip": "1"
    })
    return s

def fetch_bootstrap(session, cfg):
    url = f"{cfg['api_base']}/bootstrap"
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            app_session = r.headers.get("x-vyro-app-session")
            if app_session:
                session.headers["x-vyro-app-session"] = app_session
            return r.json()
        log(f"Gagal bootstrap (HTTP {r.status_code}): {r.text[:200]}")
    except Exception as e:
        log(f"Error fetching bootstrap: {e}")
    return None

def claim_mining(session, cfg, session_id):
    url = f"{cfg['api_base']}/mining/claim"
    payload = {
        "sessionId": session_id,
        "idempotencyKey": str(uuid.uuid4())
    }
    try:
        session.headers["Content-Type"] = "application/json"
        r = session.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            reward_raw = data.get("rewardRaw", "0")
            reward_vyro = float(reward_raw) / 1e9
            log(">> KLAIM VYRO BERHASIL! <<")
            log(f"Reward Diklaim : +{reward_vyro:.6f} VYRO")
            return True, data
        log(f"Gagal klaim VYRO (HTTP {r.status_code}): {r.text[:200]}")
    except Exception as e:
        log(f"Error claiming VYRO: {e}")
    return False, None

def run_loop():
    log("=== VYRO ($VYRO) Auto-Farmer Started ===")

    while True:
        try:
            cfg = load_config()
            session = create_session(cfg)
            boot = fetch_bootstrap(session, cfg)

            if not boot:
                log("Gagal memuat bootstrap. Coba lagi dalam 60 detik...")
                time.sleep(60)
                continue

            user = boot.get("user", {})
            mining = boot.get("mining", {})
            miner = boot.get("miner", {})
            balances = boot.get("balances", {})

            pool_raw = float(balances.get("poolRaw", 0))
            bal_vyro = pool_raw / 1e9

            speed_sec = float(miner.get("speedRawPerSecond", 57870)) / 1e9
            daily_rate = speed_sec * 86400.0  # VYRO / hari

            status = mining.get("status", "UNKNOWN")
            session_id = mining.get("sessionId")
            next_claim_iso = mining.get("nextClaimAt")
            earning_stops_iso = mining.get("earningStopsAt")

            # Check if claim is ready
            now_iso = datetime.now(timezone.utc).isoformat()
            claim_ready = False
            if next_claim_iso:
                claim_ready = datetime.fromisoformat(next_claim_iso.replace("Z", "+00:00")) <= datetime.now(timezone.utc)

            interval = cfg.get("claim_interval_seconds", 1800)
            next_claim_time = (datetime.now() + timedelta(seconds=interval)).strftime("%H:%M:%S")

            log("==================================================")
            log(f"User          : {user.get('displayName')} (@{user.get('username')})")
            log(f"Total Saldo   : {bal_vyro:.4f} VYRO")
            log(f"Mining Rate   : +{daily_rate:.2f} VYRO/hari (Speed: {miner.get('currentSpeed', '0.20')} TH/s)")
            log(f"Mining Active : True (Status: {status})")
            log(f"Klaim Siap    : {claim_ready}")
            log(f"Klaim berikutnya: {next_claim_time} WIB (~{interval // 60} menit)")
            log("==================================================")

            if claim_ready and session_id:
                success, _ = claim_mining(session, cfg, session_id)
                if success:
                    time.sleep(3)
                    # Refresh to get updated pool balance
                    new_boot = fetch_bootstrap(session, cfg)
                    if new_boot:
                        new_pool = float(new_boot.get("balances", {}).get("poolRaw", 0)) / 1e9
                        log(f"Total Saldo   : {new_pool:.4f} VYRO")

            log(f"Tidur selama {interval} detik (~{interval // 60} menit)...")
            time.sleep(interval)

        except KeyboardInterrupt:
            log("Farmer dihentikan oleh pengguna.")
            break
        except Exception as e:
            log(f"Unexpected error in farmer loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_loop()
