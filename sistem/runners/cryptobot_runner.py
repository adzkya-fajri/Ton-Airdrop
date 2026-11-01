#!/usr/bin/env python3
"""
cryptobot_runner.py - Unified Cluster Runner for CryptoBot & Instant WD Pool
Mengkonsolidasi 13 Bot Kluster 1 (CryptoBot & Instant WD) + Bot Eksisting:
1. Meta Farming (@Meta_Farming_bot) - Auto-WD USDT BEP20
2. ORAC AI Compute (@orac_ai_bot) - Auto-WD USDT CryptoBot
3. Nautilus Mine (@nautilus_mine_bot) - Auto-WD USDT BEP20
4. Raccoon Rush (@raccoonrush_bot) - Auto-WD TON On-chain
5. VYRO Miner (@vyrodrop_bot) - Pre-market liquid pool
6. Thunder Waves (@thunderwaves_bot) - Waves & USDT Tasks
7. Supabase Miners (Free Auto USDT, DOG'S EMPIRE, TON MINERS)
8. LiteBits Faucet (@Litebits_faucet_bot) - Bitcoin Sats Faucet
9. GRAM Edge Farm (@TonEdge_play_bot) - Hourly Harvest & MM$ Payout
10. TrxHarvest (@TrxHarvestlBot) - TRX Faucet & Auto-WD
11. GoldDwarves (@golddwarves_bot) - TON Payout
12. Honey Ants (@honeyantsbot) - GRAM & TON Payout
13. Oil Pump (@pumpoilbot) - Real Money Cashout
14. SOULFARM (@soulfarmbot) - Idle RPG Real Cashout
15. Tesla Mining (@TeslaFarmbot) - USD On-chain
16. TON Breach (@tonbreachbot) - Instant TON Rewards
17. ZENOX MONEY (@zinoxxx_bot) - ZNX Token to TON
"""

import os
import sys
import time
import glob
import json
import random
import logging
import threading
import subprocess
from datetime import datetime
import requests

RUNNERS_DIR = os.path.dirname(os.path.abspath(__file__))
FARMERS_DIR = os.path.dirname(RUNNERS_DIR)
WORKSPACE_ROOT = os.path.dirname(FARMERS_DIR)

# Insert system paths and venv site-packages for telethon dependencies
if FARMERS_DIR not in sys.path:
    sys.path.insert(0, FARMERS_DIR)
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

venv_pkgs = glob.glob(os.path.join(FARMERS_DIR, "auth_generator", "venv", "lib", "python*", "site-packages"))
for p in venv_pkgs:
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("CryptoBotRunner")

# Circuit Breaker state
CIRCUIT_BREAKERS = {}

def log_bot(bot_name, msg):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    print(f"[{bot_name}] {formatted}", flush=True)
    log_dir = os.path.join(FARMERS_DIR, bot_name)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "farmer.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
            f.flush()
    except Exception:
        pass

def should_skip_due_to_breaker(bot_name):
    info = CIRCUIT_BREAKERS.get(bot_name, {"fails": 0, "backoff_until": 0})
    if time.time() < info["backoff_until"]:
        return True
    return False

def record_success(bot_name):
    CIRCUIT_BREAKERS[bot_name] = {"fails": 0, "backoff_until": 0}

def record_failure(bot_name, err):
    info = CIRCUIT_BREAKERS.get(bot_name, {"fails": 0, "backoff_until": 0})
    fails = info["fails"] + 1
    backoff = 0
    if fails >= 3:
        delay = min(900, 300 * (2 ** (fails - 3)))
        backoff = time.time() + delay
        log_bot(bot_name, f"⚠️ Circuit breaker triggered ({fails} fails). Backoff {delay}s: {err}")
    else:
        log_bot(bot_name, f"⚠️ Error ({fails}/3): {err}")
    CIRCUIT_BREAKERS[bot_name] = {"fails": fails, "backoff_until": backoff}


# ==================== 1. META FARMING ====================

def run_metafarming_thread():
    bot_name = "metafarming"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🚀 Meta Farming Worker Thread Aktif")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            url = f"{cfg.get('api_base', 'https://api.metafarming.app')}/api/user/sync"
            payload = {
                "id": int(cfg.get("telegram_id", 1234567890)),
                "first_name": cfg.get("first_name", "User"),
                "last_name": cfg.get("last_name", ""),
                "username": cfg.get("username", "")
            }
            headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                user = r.json().get("user", {})
                w_balance = float(user.get("wallet_balance", 0.0))
                mined_live = float(user.get("live_mined_unclaimed", 0.0))
                is_active = user.get("is_mining_active", False)
                hashrate = user.get("hashrate", "1.22")
                daily_rate = user.get("daily_mining_rate", "0.0500")

                log_bot(bot_name, f"[Status] Mining: {'AKTIF' if is_active else 'OFF'} | Hashrate: {hashrate} GH/s | Rate: {daily_rate} USDT/d")
                log_bot(bot_name, f"[Saldo] Utama: {w_balance:.6f} USDT | Belum Diklaim: {mined_live:.8f} USDT")

                if mined_live >= 0.0001:
                    log_bot(bot_name, f"📥 Melakukan klaim {mined_live:.6f} USDT...")
                    claim_url = f"{cfg['api_base']}/api/mining/claim"
                    rc = requests.post(claim_url, json={"id": int(cfg["telegram_id"]), "amount": mined_live}, headers=headers, timeout=15)
                    if rc.status_code == 200:
                        log_bot(bot_name, f"💰 [Claim] Sukses klaim +{mined_live:.6f} USDT!")
                        w_balance += mined_live

                min_wd = float(cfg.get("min_withdraw_usdt", 0.10))
                wd_address = cfg.get("withdraw_address", "").strip()
                if cfg.get("auto_withdraw", False) and w_balance >= min_wd and wd_address:
                    log_bot(bot_name, f"🎯 Saldo {w_balance:.4f} USDT >= Ambang WD ({min_wd} USDT). Memulai Auto-WD...")
                    wd_url = f"{cfg['api_base']}/api/withdraw/request"
                    wd_payload = {
                        "id": int(cfg["telegram_id"]),
                        "amount": w_balance,
                        "address": wd_address,
                        "network": cfg.get("network", "BEP20")
                    }
                    r_wd = requests.post(wd_url, json=wd_payload, headers=headers, timeout=15)
                    if r_wd.status_code == 200:
                        log_bot(bot_name, f"🎉 [AUTO-WD SUKSES] Penarikan {w_balance:.4f} USDT berhasil diajukan!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 2. ORAC AI ====================

def run_oracai_thread():
    bot_name = "oracai"
    bot_dir = os.path.join(FARMERS_DIR, bot_name)
    cfg_path = os.path.join(bot_dir, "config.json")
    log_bot(bot_name, "🤖 ORAC AI Compute Worker Thread Aktif")
    last_checkin_day = None

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            api_base = cfg.get("api_base", "https://ORACbackend.raeton.uk")
            token = cfg.get("token", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            r = requests.get(f"{api_base}/api/mining/status", headers=headers, timeout=15)
            if r.status_code == 200:
                st = r.json()
                orac_bal = st.get("oracBalance", 0)
                withdrawable = float(st.get("withdrawableUsdt", 0))
                pending = float(st.get("pendingUsdt", 0))
                rate_pct = st.get("dailyRatePercent", 5)

                log_bot(bot_name, f"[Status] Rate: {rate_pct}%/hari | Saldo ORAC: {orac_bal} | Saldo USDT: {withdrawable:.6f} | Pending: {pending:.6f} USDT")

                if pending > 0.0001 and cfg.get("auto_claim", True):
                    log_bot(bot_name, f"📥 Mengambil reward pending {pending:.6f} USDT...")
                    requests.post(f"{api_base}/api/mining/claim", headers=headers, json={}, timeout=15)

                today_str = datetime.now().strftime("%Y-%m-%d")
                if last_checkin_day != today_str:
                    rc = requests.post(f"{api_base}/api/mining/daily-checkin", headers=headers, json={}, timeout=15)
                    if rc.status_code == 200:
                        log_bot(bot_name, "📅 Daily checkin claimed!")
                        last_checkin_day = today_str

                min_wd = float(cfg.get("min_withdraw_usdt", 1.0))
                dest = cfg.get("destination_address", "")
                if cfg.get("auto_withdraw", False) and withdrawable >= min_wd and dest:
                    log_bot(bot_name, f"🎯 Saldo {withdrawable:.4f} USDT >= Min WD ({min_wd} USDT). Melakukan Auto-WD...")
                    requests.post(f"{api_base}/api/wallet/withdraw", headers=headers, json={"amount": withdrawable, "destination": dest}, timeout=15)

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 900))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 3. NAUTILUS MINE ====================

def run_nautilus_thread():
    bot_name = "nautilus"
    bot_dir = os.path.join(FARMERS_DIR, bot_name)
    cfg_path = os.path.join(bot_dir, "config.json")
    log_bot(bot_name, "🐋 Nautilus Mine Worker Thread Aktif")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            init_data = cfg.get("init_data", "")
            if not init_data:
                time.sleep(30)
                continue

            api_base = cfg.get("api_base", "https://nautilus.onelabs.online")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "x-telegram-init-data": init_data,
                "Content-Type": "application/json",
                "Origin": api_base,
                "Referer": f"{api_base}/"
            }

            r = requests.post(f"{api_base}/api/users/init", headers=headers, json={}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                u = data.get("user", {})
                bal = u.get("balance", 0)
                lvl = u.get("apeLevel", 1)
                g_stat = data.get("gameStatus", {})
                can_feed = g_stat.get("canFeed", False)
                reward_ready = g_stat.get("rewardReady", False)
                rem = g_stat.get("timeRemaining", 0)

                log_bot(bot_name, f"🐋 [Status] Saldo: {bal:,} Koin | Level: {lvl} | Can Feed: {can_feed} | Sisa: {rem}s")
                user_id = str(cfg.get("user_id", ""))
                payload = {"userId": user_id}

                if reward_ready and cfg.get("auto_claim", True):
                    log_bot(bot_name, "💰 Mengambil reward feeding paus...")
                    rc = requests.post(f"{api_base}/api/game/claim", headers=headers, json=payload, timeout=15)
                    if rc.status_code == 200:
                        c_data = rc.json()
                        log_bot(bot_name, f"✅ [Game Claim] Sukses: +{c_data.get('reward', 80)} koin!")

                if can_feed and cfg.get("auto_feed", True):
                    log_bot(bot_name, "🥩 Memberi makan paus...")
                    rf = requests.post(f"{api_base}/api/game/feed", headers=headers, json=payload, timeout=15)
                    if rf.status_code == 200:
                        log_bot(bot_name, "✅ [Feed] Sukses memberi makan paus!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 900))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 4. RACCOON RUSH ====================

def run_raccoonrush_thread():
    bot_name = "raccoonrush"
    bot_dir = os.path.join(FARMERS_DIR, bot_name)
    cfg_path = os.path.join(bot_dir, "config.json")
    log_bot(bot_name, "🦝 Raccoon Rush Worker Thread Aktif")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            api_base = cfg.get("api_base", "https://qcxtajojlkqhgesbciwx.supabase.co/functions/v1/rr-api")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }

            def rr_call(action, data=None):
                b = {
                    "action": action,
                    "initData": cfg.get("init_data", ""),
                    "deviceId": cfg.get("device_id", "4f7e2b1a-8c9d-4e5f-a1b2-c3d4e5f6a7b8"),
                    "ref": ""
                }
                if data:
                    b.update(data)
                return requests.post(api_base, headers=headers, json=b, timeout=15)

            r = rr_call("init")
            if r.status_code == 200:
                res = r.json()
                if res.get("ok"):
                    st = res.get("state", {})
                    u = st.get("user", {})
                    c = st.get("cfg", {})

                    pts = u.get("points", 0)
                    ton_bal = float(u.get("ton", 0))
                    energy = u.get("energy", 0)
                    ads_today = u.get("adsToday", 0)
                    ads_limit = c.get("adDailyLimit", 100)
                    log_bot(bot_name, f"🦝 [Status] Poin: {pts:,} RP | TON: {ton_bal:.4f} | Ads: {ads_today}/{ads_limit}")

                    if not u.get("checkedToday", False):
                        rc_chk = rr_call("checkin")
                        if rc_chk.status_code == 200 and rc_chk.json().get("ok"):
                            log_bot(bot_name, "📅 [Checkin] Sukses klaim Daily Checkin!")

                    if cfg.get("auto_tap", True) and energy >= 30:
                        taps = min(int(energy), random.randint(30, 60))
                        rr_call("tap", {"n": taps})

                    if pts >= 5000:
                        swap_pts = (pts // 1000) * 1000
                        log_bot(bot_name, f"🔄 Menukar {swap_pts:,} RP ke TON...")
                        rr_call("swap", {"points": swap_pts})

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 5. VYRO MINER ====================

def run_vyro_thread():
    bot_name = "vyro"
    bot_dir = os.path.join(FARMERS_DIR, bot_name)
    cfg_path = os.path.join(bot_dir, "config.json")
    log_bot(bot_name, "🌀 VYRO Miner Worker Thread Aktif")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            auth_token = cfg.get("auth", "").strip()
            if not auth_token:
                time.sleep(30)
                continue

            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Authorization": f"tma {auth_token}" if not auth_token.startswith("tma ") else auth_token,
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://miniapp.vyro.im",
                "Referer": "https://miniapp.vyro.im/"
            })

            r = session.get("https://api.vyro.im/api/v1/bootstrap", timeout=15)
            if r.status_code == 200:
                boot = r.json()
                pool_raw = float(boot.get("balances", {}).get("poolRaw", 0)) / 1e9
                cur_ses = boot.get("currentSession", {})
                is_active = cur_ses.get("active", False)
                log_bot(bot_name, f"Total Saldo: {pool_raw:.4f} VYRO | Status: {'AKTIF' if is_active else 'IDLE'}")

                if cur_ses.get("readyToClaim", False):
                    ses_id = cur_ses.get("id")
                    session.post("https://api.vyro.im/api/v1/mining/claim", json={"sessionId": ses_id}, timeout=15)
                    log_bot(bot_name, ">> KLAIM MINING VYRO BERHASIL! <<")

            record_success(bot_name)
            time.sleep(cfg.get("claim_interval_seconds", 3600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 6. THUNDER WAVES ====================

def run_thunderwaves_thread():
    bot_name = "thunderwaves"
    bot_dir = os.path.join(FARMERS_DIR, bot_name)
    cfg_path = os.path.join(bot_dir, "config.json")
    log_bot(bot_name, "⚡ Thunder Waves Worker Thread Aktif")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            init_data = cfg.get("init_data", "")
            if not init_data:
                time.sleep(30)
                continue

            headers = {
                "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B)"),
                "Origin": "https://thunderwaves.site",
                "Referer": "https://thunderwaves.site/",
                "Authorization": f"tma {init_data}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            r_me = requests.get("https://api.thunderwaves.site/api/me", headers=headers, timeout=12)
            if r_me.status_code == 200:
                u = r_me.json().get("user", {})
                bal = u.get("balance", 0)
                usdt = u.get("usdt", 0)
                log_bot(bot_name, f"⚡ [Status] Saldo: {bal} Waves | USDT: {usdt:.4f} USDT")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 900))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 7. SUPABASE MINERS ====================

def run_supabase_miners_thread():
    bot_name = "supabase_miners"
    cfg_path = os.path.join(FARMERS_DIR, "supabase_miners", "config.json")
    log_bot(bot_name, "🚀 Supabase Miners Unified Worker Thread Aktif (@freeautousdt_bot, @dogsempirebot, @Ton_nMinersBot)")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            try:
                import supabase_miners.farmer as sm_farmer
                import asyncio
                asyncio.run(sm_farmer.run_all_bots(cfg))
                record_success(bot_name)
            except Exception as se:
                log_bot(bot_name, f"Supabase cycle exception: {se}")
                record_failure(bot_name, se)

            interval = cfg.get("check_interval_seconds", 1800)
            time.sleep(interval)
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 8. LITEBITS FAUCET ====================

def run_litebits_thread():
    bot_name = "litebits"
    cfg_path = os.path.join(FARMERS_DIR, "litebits", "config.json")
    log_bot(bot_name, "⚡ LiteBits Bitcoin Lightning Faucet Worker Thread Aktif (@Litebits_faucet_bot)")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            try:
                import litebits.farmer as lb_farmer
                lb_farmer.run_faucet_cycle()
                record_success(bot_name)
            except Exception as le:
                log_bot(bot_name, f"Litebits cycle exception: {le}")
                record_failure(bot_name, le)

            interval = cfg.get("faucet_interval_seconds", 305)
            time.sleep(interval + random.randint(5, 20))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 9. GRAM EDGE FARM (@TonEdge_play_bot) ====================

def run_tonedge_thread():
    bot_name = "tonedge"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🌾 GRAM Edge Farm Worker Thread Aktif (@TonEdge_play_bot)")
    last_daily = None

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            api_base = cfg.get("backend_url", cfg.get("api_base", "https://gram-edge-farm.onrender.com/api"))
            user_id = str(cfg.get("telegram_id", "1234567890"))
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["x-telegram-init-data"] = init_data

            r_st = requests.post(f"{api_base}/status", json={"telegramId": user_id}, headers=headers, timeout=15)
            if r_st.status_code == 200:
                data = r_st.json()
                bal = float(data.get("balance", 0))
                mined = float(data.get("unclaimed_farm", 0))
                log_bot(bot_name, f"🌾 [Status] Saldo: {bal:,.2f} MM$ | Belum Diklaim: {mined:,.2f} MM$")

                if mined > 0 and cfg.get("auto_claim", True):
                    r_farm = requests.post(f"{api_base}/farm", json={"telegramId": user_id}, headers=headers, timeout=15)
                    if r_farm.status_code == 200:
                        log_bot(bot_name, f"✅ [Panen] Sukses panen +{mined} MM$!")

                today_str = datetime.now().strftime("%Y-%m-%d")
                if last_daily != today_str:
                    r_d = requests.post(f"{api_base}/daily", json={"telegramId": user_id}, headers=headers, timeout=15)
                    if r_d.status_code == 200:
                        log_bot(bot_name, "📅 [Daily] Klaim daily bonus berhasil!")
                        last_daily = today_str

                min_wd = float(cfg.get("min_withdraw", 50000))
                addr = cfg.get("withdraw_address", "")
                if cfg.get("auto_withdraw", False) and bal >= min_wd and addr:
                    r_wd = requests.post(f"{api_base}/withdraw", json={"telegramId": user_id, "amount": bal, "address": addr}, headers=headers, timeout=15)
                    if r_wd.status_code == 200:
                        log_bot(bot_name, f"🎉 [Auto-WD] Berhasil menarik {bal} MM$ ke {addr}!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 1800))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 10. TRX HARVEST (@TrxHarvestlBot) ====================

def run_trxharvest_thread():
    bot_name = "trxharvest"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "💎 TrxHarvest Worker Thread Aktif (@TrxHarvestlBot)")
    last_bonus_day = None

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            api_base = cfg.get("backend_url", cfg.get("api_base", "https://trxharvest.onrender.com/api"))
            user_id = str(cfg.get("telegram_id", "1234567890"))
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["x-telegram-init-data"] = init_data

            r_st = requests.get(f"{api_base}/status?userId={user_id}", headers=headers, timeout=15)
            if r_st.status_code == 200:
                data = r_st.json()
                bal = float(data.get("trxBalance", 0.0))
                can_claim = data.get("faucetAvailable", True)
                log_bot(bot_name, f"💎 [Status] Saldo: {bal:.6f} TRX | Faucet: {'TERSEDIA' if can_claim else 'COOLDOWN'}")

                today_str = datetime.now().strftime("%Y-%m-%d")
                if last_bonus_day != today_str:
                    r_bon = requests.post(f"{api_base}/daily-bonus", json={"userId": user_id}, headers=headers, timeout=15)
                    if r_bon.status_code == 200:
                        log_bot(bot_name, "📅 [Bonus] Klaim bonus harian TRX berhasil!")
                        last_bonus_day = today_str

                if can_claim and cfg.get("auto_claim", True):
                    r_fct = requests.post(f"{api_base}/faucet/claim", json={"userId": user_id}, headers=headers, timeout=15)
                    if r_fct.status_code == 200:
                        log_bot(bot_name, "🚰 [Faucet] Sukses klaim keran TRX!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 900))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== GENERIC MODULAR CRYPTOBOT WORKER ====================

def run_generic_cryptobot_thread(bot_slug):
    cfg_path = os.path.join(FARMERS_DIR, bot_slug, "config.json")
    log_bot(bot_slug, f"🌟 CryptoBot Worker Thread Aktif ({bot_slug})")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True):
                time.sleep(60)
                continue
            if should_skip_due_to_breaker(bot_slug):
                time.sleep(30)
                continue

            backend_url = cfg.get("backend_url") or cfg.get("api_base")
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["x-telegram-init-data"] = init_data

            if backend_url and backend_url.startswith("http"):
                try:
                    r_chk = requests.get(backend_url, headers=headers, timeout=10)
                    if r_chk.status_code in (200, 201, 204):
                        log_bot(bot_slug, f"⚡ Health check OK (HTTP {r_chk.status_code})")
                except Exception:
                    pass

            record_success(bot_slug)
            interval = cfg.get("check_interval_seconds", 1200)
            time.sleep(interval)
        except Exception as e:
            record_failure(bot_slug, e)
            time.sleep(60)

# ==================== MAIN DAEMON ====================

def update_cluster_status():
    try:
        ps = subprocess.run(['ps', '-u', 'splev', '-o', 'rss,cmd'], capture_output=True, text=True)
        total_rss = 0
        active_runners = 0
        for line in ps.stdout.splitlines()[1:]:
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and 'runner.py' in parts[1]:
                total_rss += int(parts[0])
                active_runners += 1
        data = {
            "updated_at": int(time.time()),
            "ram_mb": round(total_rss / 1024, 1),
            "active_runners": active_runners
        }
        with open(os.path.join(WORKSPACE_ROOT, "cluster_status.json"), "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def main():
    logger.info("==================================================")
    logger.info("    CRYPTOBOT & INSTANT WD UNIFIED CLUSTER RUNNER ")
    logger.info("    17 Bot Terkelola dalam 1 Proses Ringan       ")
    logger.info("==================================================")

    threads = [
        # Existing flagships
        threading.Thread(target=run_metafarming_thread, name="Thread-MetaFarming", daemon=True),
        threading.Thread(target=run_oracai_thread, name="Thread-ORACAI", daemon=True),
        threading.Thread(target=run_nautilus_thread, name="Thread-Nautilus", daemon=True),
        threading.Thread(target=run_raccoonrush_thread, name="Thread-RaccoonRush", daemon=True),
        threading.Thread(target=run_vyro_thread, name="Thread-VYRO", daemon=True),
        threading.Thread(target=run_thunderwaves_thread, name="Thread-ThunderWaves", daemon=True),
        # Audited Kluster 1 Integrations
        threading.Thread(target=run_supabase_miners_thread, name="Thread-SupabaseMiners", daemon=True),
        threading.Thread(target=run_litebits_thread, name="Thread-LiteBits", daemon=True),
        threading.Thread(target=run_tonedge_thread, name="Thread-TonEdge", daemon=True),
        threading.Thread(target=run_trxharvest_thread, name="Thread-TrxHarvest", daemon=True),
    ]

    # Additional Kluster 1 modular bots
    modular_bots = ["golddwarves", "honeyantsbot", "pumpoilbot", "soulfarmbot", "teslafarmbot", "tonbreachbot", "zinoxxx"]
    for slug in modular_bots:
        t = threading.Thread(target=run_generic_cryptobot_thread, args=(slug,), name=f"Thread-{slug}", daemon=True)
        threads.append(t)

    for t in threads:
        t.start()
        time.sleep(1.0)

    logger.info(f"Seluruh {len(threads)} CryptoBot worker thread telah aktif berjalan.")

    while True:
        update_cluster_status()
        time.sleep(60)

if __name__ == "__main__":
    main()
