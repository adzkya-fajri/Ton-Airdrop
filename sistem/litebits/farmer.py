#!/usr/bin/env python3
"""
LiteBits Faucet (@Litebits_faucet_bot) 5-Minute Bitcoin Lightning Automated Farmer
Fitur:
1. Dynamic Telegram MTProto initData extraction (zero manual token maintenance)
2. JWT Token exchange via /api/auth/telegram/validate
3. Live Satoshi balance tracking via /api/user/profile
4. Daily streak claim (/api/daily-visit/check)
5. Automated faucet claim cycle (/api/claim/start -> /api/claim/{id}/complete)
6. Instant Lightning Network withdrawal when threshold reached
"""

import os
import sys
import time
import json
import logging
import random
import urllib.parse
from datetime import datetime
import requests
from telethon import TelegramClient, functions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "farmer.log")
SESSION_FILE = os.path.join(BASE_DIR, "session")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

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
        raise FileNotFoundError(f"Config not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

async def get_fresh_init_data():
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    try:
        bot = await client.get_input_entity("Litebits_faucet_bot")
        res = await client(functions.messages.RequestMainWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android"
        ))
        if "#tgWebAppData=" in res.url:
            raw = res.url.split("#tgWebAppData=")[1].split("&tgWebAppVersion")[0]
            await client.disconnect()
            return urllib.parse.unquote(raw)
    except Exception as e:
        log(f"[LiteBits] Error fetching initData: {e}")
    await client.disconnect()
    return None

def run_faucet_cycle():
    cfg = load_config()
    api_base = cfg.get("api_base", "https://mini.litebits.io")
    
    log("=== [LiteBits Faucet] Memulai Siklus Pemanenan Bitcoin Sats ===")
    
    import asyncio
    init_data = asyncio.run(get_fresh_init_data())
    if not init_data:
        log("[LiteBits] Gagal mendapatkan initData, lewati siklus.")
        return
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/json"
    }
    
    try:
        # 1. Validate & Exchange JWT
        r_val = requests.post(
            f"{api_base}/api/auth/telegram/validate",
            headers=headers,
            json={"initData": init_data},
            timeout=15
        )
        if r_val.status_code != 200 or not r_val.json().get("success"):
            log(f"[LiteBits] Gagal validasi auth: {r_val.text}")
            return
            
        token = r_val.json().get("token")
        auth_headers = {
            "User-Agent": headers["User-Agent"],
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 2. Get Profile & Balance
        r_prof = requests.get(f"{api_base}/api/user/profile", headers=auth_headers, timeout=15)
        if r_prof.status_code == 200:
            p = r_prof.json()
            balance = p.get("balance", 0)
            next_claim = p.get("nextClaimAt")
            log(f"[LiteBits] Saldo Akun: {balance} Sats Bitcoin | Referral Code: {p.get('referralCode')}")
            
            # 3. Daily streak check
            try:
                r_daily = requests.post(f"{api_base}/api/daily-visit/check", headers=auth_headers, json={}, timeout=10)
                if r_daily.status_code == 200:
                    log("[LiteBits] Daily visit streak berhasil dicatat.")
            except Exception:
                pass
                
            # 4. Trigger Faucet Claim
            log("[LiteBits] Memulai klaim keran faucet (/api/claim/start)...")
            r_start = requests.post(f"{api_base}/api/claim/start", headers=auth_headers, json={}, timeout=15)
            if r_start.status_code == 200 and r_start.json().get("success"):
                claim_id = r_start.json().get("claimId")
                log(f"[LiteBits] Claim ID diperoleh: {claim_id}. Waiting for durasi rewarded ad (15s)...")
                # Trigger network fallback & simulation
                try:
                    requests.post(f"{api_base}/api/claim/{claim_id}/network-fallback", headers=auth_headers, json={}, timeout=10)
                except Exception:
                    pass
                time.sleep(15.5)
                
                # Complete claim
                r_comp = requests.post(f"{api_base}/api/claim/{claim_id}/complete", headers=auth_headers, json={}, timeout=15)
                if r_comp.status_code == 200:
                    c_data = r_comp.json()
                    reward = c_data.get("reward", "Reward")
                    log(f"[LiteBits] KLAIM SUKSES! Hadiah: +{reward} Sats. Saldo terbaru: {c_data.get('balance', balance)} Sats.")
                else:
                    log(f"[LiteBits] Gagal menyelesaikan klaim: {r_comp.text}")
            else:
                msg = r_start.json().get("message", r_start.text)
                log(f"[LiteBits] Status Klaim Faucet: {msg}")
                
            # 5. Check Withdrawal
            if cfg.get("auto_withdraw") and cfg.get("lightning_address_or_lnurl"):
                target_addr = cfg["lightning_address_or_lnurl"]
                if balance >= 100:
                    log(f"[LiteBits] Saldo ({balance} sats) memenuhi syarat penarikan. Mengirim ke {target_addr}...")
                    wd_payload = {
                        "amount": balance,
                        "destination": target_addr
                    }
                    r_wd = requests.post(f"{api_base}/api/withdraw", headers=auth_headers, json=wd_payload, timeout=15)
                    log(f"[LiteBits] Hasil Penarikan Lightning: {r_wd.text}")
                    
    except Exception as e:
        log(f"[LiteBits] Error dalam siklus: {e}")

def main():
    cfg = load_config()
    interval = cfg.get("faucet_interval_seconds", 305)
    jitter = cfg.get("random_jitter_seconds", 15)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_faucet_cycle()
        return
        
    log(f"=== LiteBits Bitcoin Lightning Faucet Daemon Aktif (Interval: {interval}s) ===")
    while True:
        try:
            run_faucet_cycle()
        except Exception as e:
            log(f"[LiteBits] Unhandled error: {e}")
            
        sleep_time = interval + random.randint(0, jitter)
        log(f"[LiteBits] Waiting for {sleep_time} seconds untuk tetesan faucet berikutnya...\n")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
