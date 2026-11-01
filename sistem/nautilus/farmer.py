#!/usr/bin/env python3
"""
Nautilus Mine (@nautilusminebot) Auto-Farmer & Instant WD Daemon
OneLabs Web3 Engine:
- Auto-init & check-in harian (+170 koin)
- Auto-feed whale (setiap cooldown 3 jam -> +80 koin)
- Auto-claim reward feeding
- Auto-withdraw USDT (BSC) langsung ke CryptoBot saat threshold 1,000 koin tercapai
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
        "Content-Type": "application/json",
        "x-telegram-init-data": cfg.get("init_data", ""),
        "Origin": cfg.get("api_base", "https://nautilus.onelabs.online"),
        "Referer": f"{cfg.get('api_base', 'https://nautilus.onelabs.online')}/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
    }

def init_user(cfg):
    url = f"{cfg['api_base']}/api/users/init"
    payload = {
        "userId": str(cfg["user_id"]),
        "username": cfg.get("username", "user"),
        "firstName": cfg.get("first_name", "YourName"),
        "lastName": cfg.get("last_name", ""),
        "photoUrl": None,
        "isPremium": False,
        "refereeId": None
    }
    try:
        r = requests.post(url, json=payload, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            return r.json()
        log(f"⚠️ [Init User] HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log(f"⚠️ [Init User Error]: {e}")
    return None

def feed_whale(cfg):
    url = f"{cfg['api_base']}/api/game/feed"
    payload = {"userId": str(cfg["user_id"])}
    try:
        r = requests.post(url, json=payload, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                log("🐋 [Feed] Sukses memberi makan paus! Cooldown 3 jam dimulai.")
                return True
    except Exception as e:
        log(f"⚠️ [Feed Error]: {e}")
    return False

def claim_game(cfg):
    url = f"{cfg['api_base']}/api/game/claim"
    payload = {"userId": str(cfg["user_id"])}
    try:
        r = requests.post(url, json=payload, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                log(f"💰 [Game Claim] Sukses klaim hasil feeding: +{res.get('reward', 80)} koin!")
                return True
    except Exception as e:
        log(f"⚠️ [Claim Error]: {e}")
    return False

def do_checkin(cfg):
    url = f"{cfg['api_base']}/api/checkin"
    payload = {"userId": str(cfg["user_id"])}
    try:
        r = requests.post(url, json=payload, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                log(f"🎁 [Daily Checkin] Sukses klaim hari ke-{res.get('streak')} (+{res.get('reward')} koin)!")
                return True
    except Exception as e:
        log(f"⚠️ [Checkin Error]: {e}")
    return False

def withdraw_usdt(cfg, amount):
    url = f"{cfg['api_base']}/api/withdraw/request"
    payload = {
        "userId": str(cfg["user_id"]),
        "address": cfg.get("destination_address"),
        "network": cfg.get("network", "BSC"),
        "amount": int(amount)
    }
    try:
        r = requests.post(url, json=payload, headers=get_headers(cfg), timeout=20)
        res = r.json()
        if r.status_code == 200 and res.get("success"):
            log(f"🚀 [AUTO-WD NAUTILUS] SUKSES penarikan {amount} koin ke CryptoBot ({payload['address']})!")
            return True
        else:
            log(f"⚠️ [Withdraw Gagal]: {r.text[:120]}")
    except Exception as e:
        log(f"⚠️ [Withdraw Error]: {e}")
    return False

def run_loop():
    log("==================================================")
    log("     NAUTILUS MINE AUTO-FARMER & WD DAEMON        ")
    log("⚡ Mode: Whale Feed + Daily Checkin + Auto-WD USDT")
    log("==================================================")

    last_checkin_day = None

    while True:
        try:
            cfg = load_config()
            init_data = cfg.get("init_data", "")
            if not init_data:
                log("init_data is empty! Waiting for auto_generator to inject token...")
                time.sleep(30)
                continue

            data = init_user(cfg)
            if data and "user" in data:
                u = data["user"]
                bal = u.get("balance", 0)
                lvl = u.get("apeLevel", 1)
                g_stat = data.get("gameStatus", {})
                can_feed = g_stat.get("canFeed", False)
                reward_ready = g_stat.get("rewardReady", False)
                rem = g_stat.get("timeRemaining", 0)

                log(f"🐋 [Status] Saldo: {bal:,} Koin | Level: {lvl} | Can Feed: {can_feed} | Reward Ready: {reward_ready} | Sisa Waktu: {rem}s")

                # 1. Claim reward jika siap
                if reward_ready and cfg.get("auto_claim", True):
                    log("💰 Mengambil reward feeding paus...")
                    claim_game(cfg)

                # 2. Feed whale jika siap
                if can_feed and cfg.get("auto_feed", True):
                    log("🥩 Memberi makan paus...")
                    feed_whale(cfg)

                # 3. Daily checkin
                today_str = datetime.now().strftime("%Y-%m-%d")
                if last_checkin_day != today_str:
                    do_checkin(cfg)
                    last_checkin_day = today_str

                # 4. Auto-Withdraw jika saldo >= min_withdraw_coins
                min_wd = int(cfg.get("min_withdraw_coins", 1000))
                if cfg.get("auto_withdraw", True) and bal >= min_wd:
                    dest = cfg.get("destination_address")
                    if dest:
                        log(f"🎯 Saldo {bal} Koin >= {min_wd}! Memulai Auto-WD ke CryptoBot...")
                        withdraw_usdt(cfg, bal)

            # Siklus periksa setiap 15 minutes
            time.sleep(900)

        except Exception as e:
            log(f"⚠️ [Main Loop Exception]: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_loop()
