#!/usr/bin/env python3
"""
TRX Miner Beta (@TrxMinerBetaBot) Automated Daemon
Periodically claims mined TRX/TronPower, updates mining session, and completes missions.
"""

import os
import sys
import time
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "farmer.log")

INTERVAL_SECONDS = 1800  # 30 minutes

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_cycle():
    cfg = load_config()
    chat_id = cfg.get("chat_id")
    api_base = cfg.get("api_base", "https://whatdoyouneed.us/trxminiapp")
    init_data = cfg.get("init_data", "")

    if not init_data:
        log("[TrxMiner] init_data kosong, lewati.")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
        "X-Telegram-Init-Data": init_data,
        "Origin": "https://whatdoyouneed.us",
        "Referer": f"{api_base}/index.php"
    }

    try:
        log("=== Memulai siklus farming TRX Miner (@TrxMinerBetaBot)... ===")
        # 1. Init
        r_init = requests.get(f"{api_base}/backend.php?action=init&chat_id={chat_id}", headers=headers, timeout=15)
        if r_init.status_code == 200 and r_init.json().get("success"):
            data = r_init.json()
            balance = data.get("balance", 0)
            gh = data.get("gh", 0)
            mined = data.get("mined", 0)
            log(f"[TrxMiner] Saldo Akun: {balance:.4f} TRX | Hashrate: {gh} GH/s | Mined Pending: {mined:.6f} TRX")

            # 2. Claim jika ada mined balance
            if float(mined) > 0.0001:
                log(f"[TrxMiner] Mengklaim mined pending: {mined:.6f} TRX...")
                r_claim = requests.get(f"{api_base}/backend.php?action=claim&chat_id={chat_id}", headers=headers, timeout=15)
                if r_claim.status_code == 200:
                    c_data = r_claim.json()
                    log(f"[TrxMiner] Claim SUKSES! Saldo sekarang: {c_data.get('balance', balance):.4f} TRX")

            # 3. Mining heartbeat / keep-alive
            requests.get(f"{api_base}/backend.php?action=mining&chat_id={chat_id}", headers=headers, timeout=15)
            log("[TrxMiner] Mining keep-alive terkirim.")

    except Exception as e:
        log(f"[TrxMiner] Error: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_cycle()
        return

    log(f"=== TRX Miner Beta Daemon Dimulai (Interval: {INTERVAL_SECONDS}s) ===")
    while True:
        try:
            run_cycle()
        except Exception as e:
            log(f"Unhandled cycle error: {e}")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
