#!/usr/bin/env python3
"""
BoxTrust Multi-Faucet Automated Farmer
Supports 7 Faucets: Telefaucet, Rocket Faucet, Feyorra, Tether, Free TRX, Telegram Faucet, Binance Invite.
Performs Daily Claims, Taps (energy), and Task completions.
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

INTERVAL_SECONDS = 1800  # Run every 30 minutes

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

def run_faucet(slug, info):
    api_url = info.get("api_url")
    init_data = info.get("init_data")
    bot_name = info.get("bot", slug)

    if not init_data:
        log(f"[{bot_name}] init_data kosong, lewati.")
        return

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Telegram-Init-Data": init_data,
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
    }

    # 1. Bootstrap
    try:
        res = requests.post(api_url, headers=headers, json={"action": "bootstrap", "initData": init_data, "startParam": ""}, timeout=15)
        if res.status_code != 200:
            log(f"[{bot_name}] Bootstrap gagal: HTTP {res.status_code}")
            return
        boot_data = res.json()
        if not boot_data.get("ok"):
            log(f"[{bot_name}] Bootstrap err: {boot_data.get('error')}")
            return

        user = boot_data.get("data", {}).get("user", {})
        faucet = boot_data.get("data", {}).get("faucet", {})
        curr = faucet.get("symbol") or faucet.get("currency") or "COIN"
        balance = user.get("balance", "0")
        energy = user.get("energy", 0)
        daily_claimed = user.get("daily_claimed", False)

        log(f"[{bot_name}] Saldo: {balance} {curr} | Energy: {energy} | Daily Claimed: {daily_claimed}")

        # 2. Daily Claim
        if not daily_claimed:
            log(f"[{bot_name}] Mengklaim Daily Reward...")
            d_res = requests.post(api_url, headers=headers, json={"action": "claim_daily", "initData": init_data, "startParam": ""}, timeout=15).json()
            if d_res.get("ok"):
                r_reward = d_res.get("data", {}).get("reward", "0")
                log(f"[{bot_name}] Daily Claim SUKSES! +{r_reward} {curr}")
            else:
                log(f"[{bot_name}] Daily Claim info: {d_res.get('error')}")

        # 3. Tap claim jika energy > 0
        if energy and energy > 0:
            tap_amount = min(energy, 100)
            log(f"[{bot_name}] Melakukan Tap Farming ({tap_amount} taps)...")
            t_res = requests.post(api_url, headers=headers, json={"action": "tap", "initData": init_data, "startParam": "", "count": tap_amount}, timeout=15).json()
            if t_res.get("ok"):
                new_bal = t_res.get("data", {}).get("user", {}).get("balance", balance)
                log(f"[{bot_name}] Tap SUKSES! Saldo sekarang: {new_bal} {curr}")

        # 4. Auto-Withdraw ke FaucetPay jika saldo >= minimum
        min_wd = float(faucet.get("withdrawals", {}).get("minimum", 0.01))
        f_email = load_config().get("faucetpay_email")
        try:
            curr_bal = float(balance)
        except Exception:
            curr_bal = 0.0

        if f_email and curr_bal >= min_wd:
            log(f"[{bot_name}] Saldo ({curr_bal} {curr}) >= Min WD ({min_wd}). Mencoba Auto-Withdraw ke FaucetPay ({f_email})...")
            w_res = requests.post(api_url, headers=headers, json={
                "action": "request_withdrawal",
                "initData": init_data,
                "startParam": "",
                "method": "FaucetPay",
                "amount": str(curr_bal),
                "account": f_email
            }, timeout=15).json()
            if w_res.get("ok"):
                log(f"[{bot_name}] ✅ WITHDRAW SUKSES! {curr_bal} {curr} terkirim ke {f_email}")
            else:
                log(f"[{bot_name}] Withdraw info: {w_res.get('error')}")

        # 5. Cek Tasks
        tasks = boot_data.get("data", {}).get("tasks", [])
        for t in tasks:
            if not t.get("completed") and not t.get("claimed"):
                t_id = t.get("id")
                t_title = t.get("title", f"Task #{t_id}")
                log(f"[{bot_name}] Mencoba menyelesaikan tugas: {t_title}")
                # Mulai task
                requests.post(api_url, headers=headers, json={"action": "start_task", "initData": init_data, "startParam": "", "taskId": t_id}, timeout=15)
                time.sleep(1)
                # Klaim task
                c_res = requests.post(api_url, headers=headers, json={"action": "complete_task", "initData": init_data, "startParam": "", "taskId": t_id}, timeout=15).json()
                if c_res.get("ok"):
                    log(f"[{bot_name}] Tugas '{t_title}' SUKSES diklaim!")

    except Exception as e:
        log(f"[{bot_name}] Error interaksi: {e}")

def run_cycle():
    cfg = load_config()
    faucets = cfg.get("faucets", {})
    log(f"=== MEMULAI SIKLUS BOXTRUST FAUCET FARMER ({len(faucets)} Faucets) ===")
    for slug, info in faucets.items():
        run_faucet(slug, info)
        time.sleep(2)
    log("=== SIKLUS BOXTRUST FAUCET FARMER SELESAI ===")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_cycle()
        return

    log(f"=== BoxTrust Multi-Faucet Daemon Dimulai (Interval: {INTERVAL_SECONDS}s) ===")
    while True:
        try:
            run_cycle()
        except Exception as e:
            log(f"Unhandled cycle error: {e}")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
