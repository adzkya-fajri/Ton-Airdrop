#!/usr/bin/env python3
"""
Supabase Edge Multi-Bot Automated Farmer Daemon
Supports identical-architecture WebApp bots hosted on Supabase Functions:
1. Free Auto USDT (@freeautousdt_bot)
2. DOG'S EMPIRE (@dogsempirebot)
3. TON MINERS (@Ton_nMinersBot)

Features:
- Telethon MTProto automatic initData extraction (Zero manual token copy-paste)
- Dynamic session generation (action: session) & token caching
- Live balance & state tracking (action: state)
- Auto gate channel clearance (action: check_channels)
- Daily checkin claiming (action: checkin)
- Automatic task completion & reward claiming (action: tasks & task_complete)
- Mining & game heartbeat (action: game_play)
- Conditional automated withdrawal when threshold is reached
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
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
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

async def get_fresh_init_data(client, handle, app_url):
    """Fetch fresh initData directly via MTProto WebView Request"""
    try:
        ent = await client.get_entity(handle)
        res = await client(functions.messages.RequestWebViewRequest(
            peer=ent,
            bot=ent,
            platform="android",
            url=app_url
        ))
        if "#tgWebAppData=" in res.url:
            raw = res.url.split("#tgWebAppData=")[1].split("&tgWebAppVersion")[0]
            return urllib.parse.unquote(raw)
    except Exception as e:
        log(f"[{handle}] Error fetching initData: {e}")
    return None

def execute_bot_cycle(api_url, bot_key, bot_cfg, init_data):
    handle = bot_cfg["handle"]
    uuid = bot_cfg["uuid"]
    name = bot_cfg["name"]
    currency = bot_cfg.get("currency", "CRYPTO")
    
    log(f"\n--- [{name} (@{handle})] Memulai Siklus Farming ---")
    
    # 1. Establish Session
    session_payload = {
        "action": "session",
        "bot_id": uuid,
        "init_data": init_data
    }
    
    headers = {"Content-Type": "application/json"}
    try:
        r_sess = requests.post(api_url, json=session_payload, headers=headers, timeout=15)
        if r_sess.status_code != 200 or not r_sess.json().get("ok"):
            log(f"[{name}] Gagal inisialisasi sesi: {r_sess.text}")
            return
        
        token = r_sess.json().get("token")
        auth_headers = {
            "Content-Type": "application/json",
            "x-miniapp-session": token
        }
        
        # 2. State & Balance
        r_state = requests.post(api_url, json={"action": "state"}, headers=auth_headers, timeout=15)
        if r_state.status_code == 200 and r_state.json().get("ok"):
            u = r_state.json().get("user", {})
            bal = u.get("balance", 0)
            refs = u.get("referral_count", 0)
            log(f"[{name}] Saldo Saat Ini: {bal} {currency} | Total Referral: {refs}")
            
            # 3. Bypass Gates if any
            requests.post(api_url, json={"action": "check_channels"}, headers=auth_headers, timeout=10)
            
            # 4. Daily Checkin
            r_check = requests.post(api_url, json={"action": "checkin"}, headers=auth_headers, timeout=10)
            if r_check.status_code == 200 and r_check.json().get("ok"):
                log(f"[{name}] Daily Checkin Berhasil!")
            else:
                msg = r_check.json().get("message", "Sudah checkin / klaim hari ini")
                log(f"[{name}] Status Checkin: {msg}")
                
            # 5. Fetch & Complete Tasks
            r_tasks = requests.post(api_url, json={"action": "tasks"}, headers=auth_headers, timeout=10)
            if r_tasks.status_code == 200 and r_tasks.json().get("ok"):
                tasks = r_tasks.json().get("tasks", [])
                completed_count = 0
                for t in tasks:
                    if t.get("status") == "open":
                        tid = t.get("id")
                        tname = t.get("name", "Task")
                        treward = t.get("reward", 0)
                        # Try completing task
                        claim_res = requests.post(api_url, json={"action": "task_complete", "task_id": tid}, headers=auth_headers, timeout=10)
                        if claim_res.status_code == 200 and claim_res.json().get("ok"):
                            log(f"[{name}] Tugas '{tname}' Selesai! Reward: +{treward} {currency}")
                            completed_count += 1
                            time.sleep(random.uniform(1.5, 3.0))
                if completed_count == 0:
                    log(f"[{name}] Semua tugas terbuka telah dikerjakan atau menunggu antrean.")
                    
            # 6. Mini-game / Mining loop
            r_game = requests.post(api_url, json={"action": "game_play"}, headers=auth_headers, timeout=10)
            if r_game.status_code == 200 and r_game.json().get("ok"):
                log(f"[{name}] Game/Mining reward berhasil diklaim!")
                
            # 7. Check Withdrawal
            if bot_cfg.get("auto_withdraw") and bot_cfg.get("withdraw_address"):
                min_wd = bot_cfg.get("min_withdraw", 1.0)
                if bal >= min_wd:
                    log(f"[{name}] Saldo {bal} {currency} mencapai batas penarikan ({min_wd} {currency}). Mengirim withdraw...")
                    wd_payload = {
                        "action": "withdraw",
                        "address": bot_cfg["withdraw_address"]
                    }
                    r_wd = requests.post(api_url, json=wd_payload, headers=auth_headers, timeout=15)
                    log(f"[{name}] Hasil Penarikan: {r_wd.text}")
                    
        else:
            log(f"[{name}] Gagal membaca state: {r_state.text}")
            
    except Exception as e:
        log(f"[{name}] Error eksekusi siklus: {e}")

async def run_all_bots(cfg):
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    
    api_url = cfg.get("api_url")
    base_app = cfg.get("base_app_url")
    bots = cfg.get("bots", {})
    
    for bot_key, bot_cfg in bots.items():
        if not bot_cfg.get("enabled", True):
            continue
        
        handle = bot_cfg["handle"]
        uuid = bot_cfg["uuid"]
        app_url = f"{base_app}{uuid}"
        
        init_data = await get_fresh_init_data(client, handle, app_url)
        if init_data:
            execute_bot_cycle(api_url, bot_key, bot_cfg, init_data)
        else:
            log(f"[{handle}] Gagal mendapatkan initData.")
            
        time.sleep(random.uniform(2.0, 5.0))
        
    await client.disconnect()

def main():
    cfg = load_config()
    interval = cfg.get("check_interval_seconds", 1800)
    jitter = cfg.get("random_jitter_seconds", 30)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        import asyncio
        asyncio.run(run_all_bots(cfg))
        return
        
    log(f"=== Supabase Multi-Bot Farmer Daemon Aktif (Interval: {interval}s) ===")
    import asyncio
    while True:
        try:
            asyncio.run(run_all_bots(cfg))
        except Exception as e:
            log(f"Unhandled error in main loop: {e}")
            
        sleep_time = interval + random.randint(0, jitter)
        log(f"Cycle completed. Waiting for {sleep_time} seconds untuk siklus berikutnya...")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
