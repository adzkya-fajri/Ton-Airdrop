#!/usr/bin/env python3
"""
Raccoon Rush (@RACCOONRUSHapp) Auto-Farmer & Instant WD Daemon
Fitur:
1. Auto-init & state check
2. Auto-claim daily checkin
3. Auto-tap energy points
4. Auto-watch ads (memenuhi syarat 10 ads & panen RP)
5. Auto-swap points ke TON saat mencapai ambang
6. Auto-withdraw TON langsung on-chain saat saldo >= 0.05 TON
"""

import os
import sys
import time
import json
import logging
import random
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "farmer.log")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def log(msg):
    logging.info(msg)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def api_call(cfg, action, data=None):
    url = cfg.get("api_url", "https://qcxtajojlkqhgesbciwx.supabase.co/functions/v1/rr-api")
    body = {
        "action": action,
        "initData": cfg.get("init_data", ""),
        "deviceId": cfg.get("device_id", "4f7e2b1a-8c9d-4e5f-a1b2-c3d4e5f6a7b8"),
        "ref": ""
    }
    if data:
        body.update(data)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.json()
        log(f"⚠️ [API {action}] HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log(f"⚠️ [API {action} Error]: {e}")
    return None

def do_ad(cfg):
    # 1. start
    r1 = api_call(cfg, "ad_start")
    if not r1 or not r1.get("ok"):
        return False
    # wait minimum watch
    time.sleep(random.uniform(15.5, 17.0))
    # 2. claim
    r2 = api_call(cfg, "ad_claim")
    if r2 and r2.get("ok"):
        rew = r2.get("reward", 10)
        log(f"📺 [Ad Watched] Sukses klaim reward iklan: +{rew} RP!")
        return True
    return False

def do_tap(cfg, n=50):
    r = api_call(cfg, "tap", {"n": n})
    if r and r.get("ok"):
        log(f"⚡ [Tap] Sukses tap {n}x!")
        return True
    return False

def do_checkin(cfg):
    r = api_call(cfg, "checkin")
    if r and r.get("ok"):
        log("📅 [Checkin] Sukses klaim Daily Checkin!")
        return True
    return False

def do_swap(cfg, points):
    r = api_call(cfg, "swap", {"points": points})
    if r and r.get("ok"):
        log(f"🔄 [Swap] Sukses menukar {points} RP ke TON!")
        return True
    return False

def do_withdraw(cfg, amount, address):
    r = api_call(cfg, "withdraw", {"amount": amount, "address": address})
    if r and r.get("ok"):
        log(f"🚀 [AUTO-WD] Sukses ajukan penarikan {amount} TON ke {address}!")
        return True
    else:
        log(f"⚠️ [Withdraw Gagal]: {r}")
    return False

def run_loop():
    log("==================================================")
    log("     RACCOON RUSH AUTO-FARMER & WD DAEMON         ")
    log("⚡ Mode: Auto-Ads + Auto-Tap + Instant WD (0.05 TON)")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            init_res = api_call(cfg, "init")

            if init_res and init_res.get("ok"):
                st = init_res.get("state", {})
                u = st.get("user", {})
                c = st.get("cfg", {})

                pts = u.get("points", 0)
                ton_bal = float(u.get("ton", 0))
                energy = u.get("energy", 0)
                ads_today = u.get("adsToday", 0)
                ads_total = u.get("adsTotal", 0)
                ads_limit = c.get("adDailyLimit", 100)
                req_ads = c.get("withdrawAdsRequired", 10)
                min_wd = float(c.get("minWithdraw", 0.05))
                checked = u.get("checkedToday", False)

                log(f"🦝 [Status] Poin: {pts:,} RP | Saldo TON: {ton_bal:.4f} | Ads Total: {ads_total}/{req_ads} | Ads Hari Ini: {ads_today}/{ads_limit}")

                # 1. Daily Checkin
                if not checked:
                    do_checkin(cfg)

                # 2. Auto-Tap
                if cfg.get("auto_tap", True) and energy >= 30:
                    taps_count = min(energy, random.randint(30, 60))
                    do_tap(cfg, taps_count)

                # 3. Nonton Ads (bertahap per batch)
                max_ads = cfg.get("max_ads_per_cycle", 5)
                if cfg.get("auto_ads", True) and ads_today < ads_limit:
                    ads_done = 0
                    for _ in range(max_ads):
                        if do_ad(cfg):
                            ads_done += 1
                            time.sleep(random.uniform(5.0, 7.0))
                        else:
                            break
                    if ads_done > 0:
                        log(f"📺 Selesai batch {ads_done} iklan.")

                # 4. Auto-Swap Points -> TON jika poin >= 5,000 (0.05 TON)
                swap_rate = c.get("swapRate", 100000)
                if pts >= 5000:
                    swap_pts = (pts // 1000) * 1000
                    log(f"🔄 Menukar {swap_pts:,} RP ke saldo TON...")
                    do_swap(cfg, swap_pts)

                # 5. Auto-Withdraw TON ke wallet jika memenuhi syarat
                w_addr = cfg.get("ton_wallet_address", "")
                if cfg.get("auto_withdraw", True) and ton_bal >= min_wd:
                    if ads_total >= req_ads:
                        log(f"🎯 Saldo {ton_bal:.4f} TON >= {min_wd} & Syarat {req_ads} Ads terpenuhi! Melakukan Auto-WD...")
                        do_withdraw(cfg, ton_bal, w_addr)
                    else:
                        log(f"⏳ Saldo TON cukup ({ton_bal:.4f}), namun butuh {req_ads - ads_total} iklan lagi untuk membuka WD.")

            # Istirahat 10 minutes per siklus
            time.sleep(600)

        except Exception as e:
            log(f"⚠️ [Loop Exception]: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_loop()
