#!/usr/bin/env python3
"""
farmer.py - FROG FARM (@frogfarm01bot) Automated Farmer
Handles checkin, 4-hour timer claim, mini-games, channel tasks, auto-swap to TON, and auto-WD.
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BOT_DIR, "config.json")
LOG_PATH = os.path.join(BOT_DIR, "farmer.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("FrogFarm")

def log_farmer(msg):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now_str}] {msg}"
    print(f"[frogfarm] {line}", flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def api_call(api_url, init_data, action, extra=None):
    payload = {
        "initData": init_data,
        "action": action,
        "device": {"platform": "Android", "vendor": "Google", "screen": "1080x2400"},
        "fp": "fb89a9321c8"
    }
    if extra:
        payload.update(extra)
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36 Telegram-Android/11.2.1",
        "Origin": "https://dogs-app-one.vercel.app",
        "Referer": "https://dogs-app-one.vercel.app/"
    }
    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        log_farmer(f"API Error (HTTP {r.status_code}): {r.text[:120]}")
    except Exception as e:
        log_farmer(f"Request exception: {e}")
    return None

def run_loop():
    log_farmer("🐸 Frog Farm Worker Loop Dimulai...")
    while True:
        try:
            cfg = load_config()
            if not cfg or not cfg.get("init_data"):
                log_farmer("⚠️ init_data belum tersedia. Waiting for...")
                time.sleep(30)
                continue

            api_url = cfg.get("api_url", "https://ytrvqpjdghvjcjwtscyv.supabase.co/functions/v1/dogs-api")
            init_data = cfg.get("init_data")
            wallet_addr = cfg.get("wallet", "YOUR_TON_WALLET_ADDRESS")
            auto_swap = cfg.get("auto_swap", True)
            min_swap = cfg.get("min_swap_frogs", 800)
            auto_wd = cfg.get("auto_withdraw", True)
            min_wd = cfg.get("min_withdraw_ton", 0.05)
            interval = cfg.get("interval_sec", 300)

            # 1. State inquiry
            res = api_call(api_url, init_data, "state")
            if not res or not res.get("state"):
                log_farmer("Gagal mengambil state profil. Coba lagi siklus depan...")
                time.sleep(60)
                continue

            state = res.get("state", {})
            bal_frogs = state.get("balance", 0)
            ton_bal = state.get("ton", 0.0)
            ci_done = state.get("ci_done_today", False)
            ci_streak = state.get("ci_streak", 0)
            plays = state.get("plays", {})
            games_per_day = state.get("cfg", {}).get("games_per_day", 2)

            log_farmer(f"🐸 [Status] Saldo: {bal_frogs:,} FROGS | TON: {ton_bal:.4f} TON | Streak: {ci_streak} hari | CI Hari Ini: {'SUDAH' if ci_done else 'BELUM'}")

            # 2. Check-in harian
            if not ci_done:
                ci_res = api_call(api_url, init_data, "checkin")
                if ci_res and ci_res.get("result"):
                    r_val = ci_res.get("result", {}).get("reward", 0)
                    log_farmer(f"📅 [Check-in] Sukses check-in hari ke-{ci_res.get('result', {}).get('day')}: +{r_val} FROGS!")
                    bal_frogs = ci_res.get("state", {}).get("balance", bal_frogs)

            # 3. Klaim timer berkala (claim)
            c_res = api_call(api_url, init_data, "claim")
            if c_res and c_res.get("result"):
                rew = c_res.get("result", {}).get("reward", 0)
                log_farmer(f"🎁 [Timer Claim] Sukses klaim timer berkala: +{rew} FROGS!")
                bal_frogs = c_res.get("state", {}).get("balance", bal_frogs)

            # 4. Mainkan Wheel jika kuota masih ada
            wheel_played = plays.get("wheel", 0)
            if wheel_played < games_per_day:
                w_res = api_call(api_url, init_data, "game", {"game": "wheel"})
                if w_res and w_res.get("result"):
                    w_rew = w_res.get("result", {}).get("reward", 0)
                    log_farmer(f"🎡 [Wheel Spin] Berhasil memutar roda: +{w_rew} FROGS!")
                    bal_frogs = w_res.get("state", {}).get("balance", bal_frogs)

            # 5. Kerjakan Task jika ada
            task_list = state.get("task_list", [])
            completed_tasks = state.get("tasks", [])
            for t in task_list:
                tid = t.get("id")
                if tid not in completed_tasks:
                    time.sleep(2)
                    t_res = api_call(api_url, init_data, "task", {"task": tid})
                    if t_res and t_res.get("result") and t_res.get("result").get("reward"):
                        rew_t = t_res.get("result", {}).get("reward")
                        log_farmer(f"📋 [Task] Selesai '{t.get('title')}': +{rew_t} FROGS!")
                        bal_frogs = t_res.get("state", {}).get("balance", bal_frogs)
                    elif t_res and t_res.get("result") and t_res.get("result").get("error"):
                        pass

            # 6. Swap FROGS ke TON jika cukup
            if auto_swap and bal_frogs >= min_swap:
                log_farmer(f"🔄 Saldo {bal_frogs} FROGS >= {min_swap}. Memulai swap ke TON...")
                swap_res = api_call(api_url, init_data, "swap", {"amount": bal_frogs})
                if swap_res and swap_res.get("result") and swap_res.get("result").get("ok"):
                    ton_gained = swap_res.get("result", {}).get("ton", 0)
                    ton_bal = swap_res.get("state", {}).get("ton", ton_bal + ton_gained)
                    bal_frogs = swap_res.get("state", {}).get("balance", 0)
                    log_farmer(f"💰 [Swap Sukses] Ditukar ke +{ton_gained:.4f} TON. Saldo TON kini: {ton_bal:.4f} TON")

            # 7. Auto-Withdraw TON jika saldo memenuhi ambang
            if auto_wd and ton_bal >= min_wd:
                log_farmer(f"🎯 Saldo {ton_bal:.4f} TON >= Min WD ({min_wd} TON). Mengajukan penarikan ke {wallet_addr}...")
                wd_res = api_call(api_url, init_data, "withdraw", {"amount": ton_bal, "wallet": wallet_addr})
                if wd_res and wd_res.get("result") and not wd_res.get("result").get("error"):
                    log_farmer(f"🎉 [AUTO-WD SUKSES] Penarikan {ton_bal:.4f} TON berhasil diajukan!")
                else:
                    err = wd_res.get("result", {}).get("error") if wd_res else "Unknown"
                    log_farmer(f"⚠️ [WD Tertahan] Respon: {err}")

            time.sleep(interval)

        except Exception as e:
            log_farmer(f"Loop exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_loop()
