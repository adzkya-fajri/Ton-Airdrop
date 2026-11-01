#!/usr/bin/env python3
"""
ORAC AI Smart Cloud Mining Auto-Farmer & Auto-Withdraw Daemon
Otomasi cloud compute node mining ORAC AI (@ORAC_AIbot):
- Auto-claim pending USDT hasil mining (siklus berkala)
- Auto-claim daily checkin harian (+ORAC +USDT)
- Auto-spin lucky wheel bila tiket tersedia
- Auto-withdraw USDT (BEP20) langsung ke CryptoBot saat threshold 1 USDT tercapai
"""

import os
import sys
import time
import json
import logging
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

def get_headers(cfg):
    return {
        "Authorization": f"Bearer {cfg['token']}",
        "Content-Type": "application/json",
        "Origin": cfg.get("web_origin", "https://orac.raeton.uk"),
        "Referer": f"{cfg.get('web_origin', 'https://orac.raeton.uk')}/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
    }

def get_mining_status(cfg):
    url = f"{cfg['api_base']}/api/mining/status"
    try:
        r = requests.get(url, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                return res.get("data")
        log(f"⚠️ [Status Mining] Gagal HTTP {r.status_code}: {r.text}")
    except Exception as e:
        log(f"⚠️ [Status Mining Error]: {e}")
    return None

def claim_mining(cfg):
    url = f"{cfg['api_base']}/api/mining/claim"
    try:
        r = requests.post(url, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                data = res.get("data", {})
                claimed = data.get("claimedUsdt", 0)
                new_bal = data.get("newWithdrawableUsdt", 0)
                log(f"💰 [Mining Claim] Sukses klaim +{claimed:.6f} USDT! Total Withdrawable: {new_bal:.6f} USDT")
                return True, data
        else:
            log(f"⚠️ [Mining Claim Gagal] HTTP {r.status_code}: {r.text}")
    except Exception as e:
        log(f"⚠️ [Mining Claim Error]: {e}")
    return False, None

def claim_daily_checkin(cfg):
    url = f"{cfg['api_base']}/api/user/daily-checkin/claim"
    try:
        r = requests.post(url, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                d = res.get("data", {})
                log(f"🎁 [Daily Checkin] Sukses Streak Hari ke-{d.get('streak')} (+{d.get('rewardOrac')} ORAC, +{d.get('rewardUsdt')} USDT)!")
                return True
    except Exception as e:
        log(f"⚠️ [Daily Checkin Error]: {e}")
    return False

def spin_wheel(cfg):
    url = f"{cfg['api_base']}/api/wheel/spin"
    try:
        r = requests.post(url, json={"count": 1}, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                log("🎰 [Lucky Wheel] Berhasil spin roda keberuntungan!")
                return True
    except Exception:
        pass
    return False

def withdraw_usdt(cfg, amount):
    url = f"{cfg['api_base']}/api/wallet/withdraw/request"
    payload = {
        "amountUsdt": round(float(amount), 4),
        "currency": cfg.get("currency", "USDT"),
        "network": cfg.get("network", "BEP20"),
        "destinationAddress": cfg.get("destination_address")
    }
    try:
        r = requests.post(url, json=payload, headers=get_headers(cfg), timeout=20)
        res = r.json()
        if r.status_code == 200 and res.get("success"):
            log(f"🚀 [AUTO-WD ORAC] SUKSES! Penarikan {amount:.4f} USDT ke CryptoBot ({payload['destinationAddress']}) diajukan!")
            return True
        else:
            err = res.get("error", {}).get("message") or r.text
            log(f"⚠️ [AUTO-WD Gagal]: {err}")
    except Exception as e:
        log(f"⚠️ [AUTO-WD Error]: {e}")
    return False

def run_loop():
    log("==================================================")
    log("    ORAC AI SMART CLOUD MINING DAEMON START       ")
    log("⚡ Mode: Auto-Mine + Daily Checkin + Auto-WD USDT  ")
    log("==================================================")

    last_checkin_day = None

    while True:
        try:
            cfg = load_config()
            status = get_mining_status(cfg)

            if status:
                orac_bal = status.get("oracBalance", 0)
                withdrawable = float(status.get("withdrawableUsdt", 0))
                pending = float(status.get("pendingUsdt", 0))
                rate_pct = status.get("dailyRatePercent", 5)

                log(f"[Status] Rate: {rate_pct}%/hari | Saldo ORAC: {orac_bal} | Saldo USDT: {withdrawable:.6f} | Pending: {pending:.6f} USDT")

                # 1. Klaim pending jika > 0.0001 USDT
                if pending > 0.0001 and cfg.get("auto_claim", True):
                    log(f"📥 Mengambil reward pending {pending:.6f} USDT...")
                    claim_mining(cfg)
                    # Refresh status
                    status = get_mining_status(cfg)
                    if status:
                        withdrawable = float(status.get("withdrawableUsdt", 0))

                # 2. Checkin harian (1x sehari)
                today_str = datetime.now().strftime("%Y-%m-%d")
                if last_checkin_day != today_str:
                    log("📅 Memeriksa Daily Check-in harian...")
                    if claim_daily_checkin(cfg):
                        last_checkin_day = today_str

                # 3. Spin wheel
                spin_wheel(cfg)

                # 4. Auto-Withdraw ke CryptoBot jika >= min_withdraw_usdt
                min_wd = float(cfg.get("min_withdraw_usdt", 1.0))
                if cfg.get("auto_withdraw", True) and withdrawable >= min_wd:
                    dest = cfg.get("destination_address")
                    if dest:
                        log(f"🎯 Saldo {withdrawable:.4f} USDT >= Min WD ({min_wd} USDT). Memulai Auto-WD ke CryptoBot...")
                        withdraw_usdt(cfg, withdrawable)

            interval = int(cfg.get("claim_interval_seconds", 1800))
            time.sleep(interval)

        except Exception as e:
            log(f"⚠️ [Main Loop Exception]: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_loop()
