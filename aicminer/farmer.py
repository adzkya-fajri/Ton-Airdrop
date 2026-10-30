#!/usr/bin/env python3
"""
AIC Miner (@Aicminer_bot) Auto-Farmer Daemon
Automates:
1. Daily Check-in Streak Claim (0.1 - 0.5 AIC daily)
2. Task Verification & Claim (USDT/AIC rewards)
3. Mining Profit Claim (when wallet active & threshold met)
4. Balance and Withdrawal tracking
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
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Gagal membaca config.json: {e}")
    return {}

def run_cycle():
    cfg = load_config()
    telegram_id = str(cfg.get("telegram_id", "7672016530"))
    api_base = cfg.get("api_base", "https://api.nexogainx.com/api").rstrip("/")
    init_data = cfg.get("init_data", "")
    user_obj = cfg.get("user", {})

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "https://app.nexogainx.com",
        "Referer": "https://app.nexogainx.com/"
    }

    log("==================================================")
    log("🚀 Memulai siklus farming AIC Miner (@Aicminer_bot)...")
    log("==================================================")

    # 1. Login/Keepalive jika ada init_data
    if init_data:
        try:
            payload = {
                "initData": init_data,
                "startParam": "",
                "user": user_obj
            }
            r_login = requests.post(f"{api_base}/auth/telegram", json=payload, headers=headers, timeout=12)
            if r_login.status_code == 200:
                log("[Auth] Berhasil login/keepalive ke server AIC.")
        except Exception as ex:
            log(f"[Auth] Warning: {ex}")

    # 2. Daily Check-in Claim
    if cfg.get("auto_claim_checkin", True):
        try:
            r_chk = requests.get(f"{api_base}/tasks/checkin/status?telegramId={telegram_id}", headers=headers, timeout=10)
            if r_chk.status_code == 200:
                chk_data = r_chk.json()
                if chk_data.get("canCheckinToday"):
                    log(f"[Check-in] Tersedia klaim hari ke-{chk_data.get('currentStreakDay')} (+{chk_data.get('todayReward')} AIC). Memproses...")
                    r_claim = requests.post(f"{api_base}/tasks/checkin/claim", json={"telegramId": telegram_id}, headers=headers, timeout=10)
                    if r_claim.status_code == 200:
                        log(f"[Check-in] 🎉 Sukses klaim: {r_claim.json().get('message')}")
                    else:
                        log(f"[Check-in] Gagal klaim: {r_claim.text}")
                else:
                    log(f"[Check-in] Sudah check-in hari ini (Streak Day {chk_data.get('currentStreakDay')}).")
        except Exception as ex:
            log(f"[Check-in] Error: {ex}")

    # 3. Tasks Verification & Claim
    if cfg.get("auto_claim_tasks", True):
        try:
            r_tasks = requests.get(f"{api_base}/tasks?telegramId={telegram_id}", headers=headers, timeout=10)
            if r_tasks.status_code == 200:
                t_list = r_tasks.json().get("tasks", [])
                for t in t_list:
                    t_id = t.get("id")
                    t_title = t.get("title")
                    # Klaim tugas yang bukan invite/pembelian
                    try:
                        r_v = requests.post(f"{api_base}/tasks/verify", json={"telegramId": telegram_id, "taskId": t_id}, headers=headers, timeout=10)
                        if r_v.status_code == 200:
                            v_json = r_v.json()
                            if v_json.get("success"):
                                log(f"[Tasks] 🎉 Sukses klaim task '{t_title}': +{t.get('rewardAmount')} {t.get('rewardType')}")
                        time.sleep(1.0)
                    except Exception:
                        pass
        except Exception as ex:
            log(f"[Tasks] Error: {ex}")

    # 4. Mining Profit Claim
    if cfg.get("auto_claim_mining", True):
        try:
            r_mine = requests.post(f"{api_base}/mining/claim", json={"telegramId": telegram_id}, headers=headers, timeout=10)
            if r_mine.status_code == 200:
                log(f"[Mining] 🎉 Sukses klaim hasil tambang!")
            else:
                resp_txt = r_mine.text
                if "requiresWallet" in resp_txt:
                    log(f"[Mining] Notice: Belum terhubung TON wallet. Mining gratis aktif via check-in & saldo.")
                elif "canClaim" in resp_txt or "not ready" in resp_txt.lower():
                    log(f"[Mining] Profit belum siap diklaim.")
                else:
                    log(f"[Mining] Info: {resp_txt}")
        except Exception as ex:
            log(f"[Mining] Error: {ex}")

    # 5. Cek Saldo & Status Withdrawal
    try:
        r_wd = requests.get(f"{api_base}/withdraw/info?telegramId={telegram_id}", headers=headers, timeout=10)
        if r_wd.status_code == 200:
            wd_data = r_wd.json()
            cur_bal = wd_data.get("earningBalance", 0)
            min_wd = wd_data.get("minWithdrawAmount", 8)
            token = wd_data.get("token", "AIC")
            net = wd_data.get("network", "TON")
            log(f"[Balance] Saldo Saat Ini: {cur_bal} {token} (Batas Min WD: {min_wd} {token} via jaringan {net})")
    except Exception as ex:
        log(f"[Balance] Gagal membaca saldo: {ex}")

    log("Siklus AIC Miner selesai.")
    return True

def main_loop():
    cfg = load_config()
    interval = cfg.get("cycle_interval_seconds", 1800)
    log(f"=== AIC Miner Auto-Farmer Daemon Dimulai (Interval: {interval}s) ===")
    while True:
        try:
            run_cycle()
        except Exception as e:
            log(f"Error loop utama: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_cycle()
    else:
        main_loop()
