#!/usr/bin/env python3
"""
Meta Farming Cloud USDT Auto-Farmer & Auto-Withdraw Daemon
Otomasi cloud mining mikro USDT (@Meta_Farming_bot):
- Auto-sync profil & keep-alive mining
- Auto-start mining sesi 24 jam bila idle/berhenti
- Auto-claim balance tertambang ke wallet balance (min 0.0001 USDT)
- Auto-withdraw instan (min 0.10 USDT BEP20) saat threshold tercapai
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

def sync_user(cfg):
    url = f"{cfg['api_base']}/api/user/sync"
    payload = {
        "id": int(cfg["telegram_id"]),
        "first_name": cfg.get("first_name", "User"),
        "last_name": cfg.get("last_name", ""),
        "username": cfg.get("username", "")
    }
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("user")
        else:
            log(f"⚠️ [Sync] HTTP {r.status_code}: {r.text}")
    except Exception as e:
        log(f"⚠️ [Sync Error]: {e}")
    return None

def start_mining(cfg):
    url = f"{cfg['api_base']}/api/mining/start"
    payload = {"userId": str(cfg["telegram_id"])}
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                log("⚡ [Mining] Sesi mining berhasil dinyalakan / diperpanjang!")
                return True
        log(f"⚠️ [Mining Start] Respon: {r.text}")
    except Exception as e:
        log(f"⚠️ [Mining Start Error]: {e}")
    return False

def claim_mined(cfg, amount):
    url = f"{cfg['api_base']}/api/claim"
    payload = {
        "userId": str(cfg["telegram_id"]),
        "amount": round(float(amount), 6),
        "restart": False
    }
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        res = r.json()
        if r.status_code == 200 and res.get("success"):
            log(f"💰 [Claim] Sukses klaim +{amount:.6f} USDT ke Saldo Utama!")
            return True, res
        else:
            err = res.get("error") or res.get("message") or r.text
            log(f"⚠️ [Claim Gagal]: {err}")
    except Exception as e:
        log(f"⚠️ [Claim Error]: {e}")
    return False, None

def withdraw_usdt(cfg, amount, address):
    url = f"{cfg['api_base']}/api/withdraw"
    payload = {
        "userId": str(cfg["telegram_id"]),
        "telegramId": str(cfg["telegram_id"]),
        "username": cfg.get("username", ""),
        "firstName": cfg.get("first_name", ""),
        "lastName": cfg.get("last_name", ""),
        "amount": round(float(amount), 4),
        "address": address,
        "network": cfg.get("network", "BEP20")
    }
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        res = r.json()
        if r.status_code == 200 and res.get("success"):
            log(f"🚀 [AUTO-WD] SUKSES! Penarikan {amount:.4f} USDT ke {address} berhasil diajukan!")
            return True, res
        else:
            err = res.get("error") or res.get("message") or r.text
            log(f"⚠️ [AUTO-WD Gagal]: {err}")
    except Exception as e:
        log(f"⚠️ [AUTO-WD Error]: {e}")
    return False, None

def run_loop():
    log("==================================================")
    log("🚀 META FARMING AUTO-FARMER & AUTO-WD DAEMON START")
    log("⚡ Mode: Auto-Mine + Auto-Claim + Auto-Withdraw USDT")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            user = sync_user(cfg)

            if user:
                w_balance = float(user.get("wallet_balance", 0.0))
                mined_live = float(user.get("live_mined_unclaimed", 0.0))
                is_active = user.get("is_mining_active", False)
                hashrate = user.get("hashrate", "1.22")
                daily_rate = user.get("daily_mining_rate", "0.0500")

                log(f"[Status] Mining: {'AKTIF' if is_active else 'OFF'} | Hashrate: {hashrate} GH/s | Rate: {daily_rate} USDT/d")
                log(f"[Saldo] Utama: {w_balance:.6f} USDT | Belum Diklaim: {mined_live:.8f} USDT")

                # 1. Pastikan mining selalu aktif
                if not is_active:
                    log("⛏️ Mining tidak aktif. Mengirim request start...")
                    start_mining(cfg)

                # 2. Klaim jika belum diklaim >= 0.0001 USDT
                if mined_live >= 0.0001:
                    log(f"📥 Melakukan klaim {mined_live:.6f} USDT...")
                    claimed_ok, _ = claim_mined(cfg, mined_live)
                    if claimed_ok:
                        # Refresh data setelah claim
                        user = sync_user(cfg)
                        if user:
                            w_balance = float(user.get("wallet_balance", 0.0))

                # 3. Auto-Withdraw jika threshold tercapai
                min_wd = float(cfg.get("min_withdraw_usdt", 0.10))
                wd_address = cfg.get("withdraw_address", "").strip()

                if cfg.get("auto_withdraw", True) and w_balance >= min_wd:
                    if wd_address:
                        log(f"🎯 Saldo {w_balance:.4f} USDT >= Ambang WD ({min_wd} USDT). Memulai Auto-WD...")
                        withdraw_usdt(cfg, w_balance, wd_address)
                    else:
                        log(f"⚠️ Saldo siap WD ({w_balance:.4f} USDT >= {min_wd}), tetapi withdraw_address di config.json belum diisi!")

            interval = int(cfg.get("claim_interval_seconds", 600))
            time.sleep(interval)

        except Exception as e:
            log(f"⚠️ [Loop Exception]: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_loop()
