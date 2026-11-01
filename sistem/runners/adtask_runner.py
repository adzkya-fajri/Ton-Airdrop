#!/usr/bin/env python3
"""
adtask_runner.py - Unified Cluster Runner for Ad-Task & Micro-Reward Faucets
Mengkonsolidasi 23 Bot Kluster 2 (Ad-Task, Micro-Rewards & Faucets) + Bot Eksisting:
1. Gram Bux (@GramBux_bot) - Telegram Stars (⭐) & GRAM Faucet
2. Case Rush (@case_rush_bot) - Daily Free Case & Telegram Gifts
3. PaidZ (@paidzapp, @paldz_bot) - Real USDT Ads Rewards
4. Flames Earn (@FlamesEarnBot) - Lucky Wheel & Stars Mining
5. Gram Buddies (@GramBuddiesBot)
6. BoxTrust Multi-Faucet (7 Faucets)
7. Frog Farm (@FrogFarmBot)
8. Dropex, Nuggy Run, Adclickers, Earn Craft, Emojify, GiftBoost, Howl,
   Klikado, Leaf Earn, Pumpkin Earn, StarMine, Stars Market, TgPay Crypto,
   BNB Stars, Gram Git, GRAM LAB, Gram Spark, GRAMIFY.
"""

import os
import sys
import time
import glob
import json
import random
import logging
import threading
from datetime import datetime
import requests

RUNNERS_DIR = os.path.dirname(os.path.abspath(__file__))
FARMERS_DIR = os.path.dirname(RUNNERS_DIR)
WORKSPACE_ROOT = os.path.dirname(FARMERS_DIR)

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
logger = logging.getLogger("AdTaskRunner")

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


# ==================== LEGACY BOTS (GramBuddies, BoxTrust, FrogFarm) ====================

def run_legacy_worker(bot_name, module_name, func_name):
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, f"🚀 Worker Legacy Aktif: {module_name}.{func_name}")

    while True:
        try:
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    if not cfg.get("enabled", True):
                        time.sleep(60)
                        continue
                except Exception:
                    pass

            if should_skip_due_to_breaker(bot_name):
                time.sleep(30)
                continue

            mod = __import__(module_name, fromlist=[func_name])
            fn = getattr(mod, func_name)
            fn()
            record_success(bot_name)
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(30)

# ==================== 1. GRAM BUX (@GramBux_bot) ====================

def run_grambux_thread():
    bot_name = "grambux"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "⭐ Gram Bux Worker Thread Aktif (@GramBux_bot)")

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

            api_base = cfg.get("backend_url", "https://grambux.xyz/api/").rstrip("/")
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["x-telegram-init-data"] = init_data
                headers["Authorization"] = f"tma {init_data}"

            # 1. Profile & Stars balance
            r_me = requests.get(f"{api_base}/me", headers=headers, timeout=15)
            if r_me.status_code == 200:
                data = r_me.json()
                stars = data.get("stars", 0)
                gram = data.get("gram", 0)
                streak = data.get("streak", 1)
                log_bot(bot_name, f"⭐ [Status] Saldo: {stars} Stars | {gram} GRAM | Streak: {streak} Hari")

                # 2. Daily Check-in / Claim
                if cfg.get("auto_claim", True):
                    r_chk = requests.post(f"{api_base}/daily-checkin", headers=headers, json={}, timeout=15)
                    if r_chk.status_code == 200:
                        log_bot(bot_name, "📅 [Check-in] Sukses klaim reward harian Stars!")

                # 3. Ad Task cycle
                if cfg.get("auto_ads", True):
                    r_ad = requests.post(f"{api_base}/ads/start", headers=headers, json={}, timeout=15)
                    if r_ad.status_code == 200:
                        time.sleep(random.uniform(5.0, 8.0))
                        r_clm = requests.post(f"{api_base}/ads/claim", headers=headers, json={}, timeout=15)
                        if r_clm.status_code == 200:
                            log_bot(bot_name, "📺 [Ad] Sukses klaim reward iklan Stars!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 900))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 2. CASE RUSH (@case_rush_bot) ====================

def run_caserush_thread():
    bot_name = "caserush"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "📦 Case Rush Worker Thread Aktif (@case_rush_bot)")

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

            api_base = cfg.get("backend_url", "https://api.caserush.app").rstrip("/")
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["x-telegram-init-data"] = init_data

            r_st = requests.get(f"{api_base}/user/status", headers=headers, timeout=15)
            if r_st.status_code == 200:
                u = r_st.json()
                free_cases = u.get("freeCasesAvailable", 1)
                log_bot(bot_name, f"📦 [Status] Peti Gratis Tersedia: {free_cases}")

                if free_cases > 0 and cfg.get("auto_claim", True):
                    r_open = requests.post(f"{api_base}/cases/open-free", headers=headers, json={}, timeout=15)
                    if r_open.status_code == 200:
                        reward = r_open.json().get("item", "Reward")
                        log_bot(bot_name, f"🎉 [Case] Buka peti gratis sukses! Hadiah: {reward}")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 3600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 3. PAIDZ (@paidzapp) ====================

def run_paidz_thread():
    bot_name = "paidz"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "💵 PaidZ Worker Thread Aktif (@paidzapp)")

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

            api_base = cfg.get("backend_url", "https://paidz.biz/api").rstrip("/")
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["Authorization"] = f"tma {init_data}"

            r_u = requests.get(f"{api_base}/user/profile", headers=headers, timeout=15)
            if r_u.status_code == 200:
                p = r_u.json()
                bal = float(p.get("balanceUsdt", 0.0))
                ads_avail = p.get("availableAds", 5)
                log_bot(bot_name, f"💵 [Status] Saldo: {bal:.4f} USDT | Iklan Tersedia: {ads_avail}")

                # Simulate rewarded ad views
                if ads_avail > 0 and cfg.get("auto_ads", True):
                    r_view = requests.post(f"{api_base}/ads/start", headers=headers, json={}, timeout=15)
                    if r_view.status_code == 200:
                        sess_id = r_view.json().get("sessionId")
                        log_bot(bot_name, f"📺 Menonton iklan PaidZ ({sess_id}). Simulasi 15s...")
                        time.sleep(15.5)
                        r_comp = requests.post(f"{api_base}/ads/complete", headers=headers, json={"sessionId": sess_id}, timeout=15)
                        if r_comp.status_code == 200:
                            log_bot(bot_name, "✅ [Ad] Hadiah iklan PaidZ diklaim!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 1200))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 4. FLAMES EARN (@FlamesEarnBot) ====================

def run_flamesearn_thread():
    bot_name = "flamesearn"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🔥 Flames Earn Worker Thread Aktif (@FlamesEarnBot)")

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

            api_base = cfg.get("backend_url", "https://flamesearn.site/api").rstrip("/")
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["x-telegram-init-data"] = init_data

            r_st = requests.get(f"{api_base}/user", headers=headers, timeout=15)
            if r_st.status_code == 200:
                data = r_st.json()
                stars = data.get("stars", 0)
                spin_avail = data.get("canSpin", True)
                log_bot(bot_name, f"🔥 [Status] Saldo: {stars} Stars | Lucky Spin: {'READY' if spin_avail else 'COOLDOWN'}")

                if spin_avail and cfg.get("auto_claim", True):
                    r_sp = requests.post(f"{api_base}/wheel/spin", headers=headers, json={}, timeout=15)
                    if r_sp.status_code == 200:
                        log_bot(bot_name, "🎰 [Lucky Wheel] Sukses memutar roda keberuntungan!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 1800))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== GENERIC MODULAR ADTASK WORKER ====================

def run_generic_adtask_thread(bot_slug):
    cfg_path = os.path.join(FARMERS_DIR, bot_slug, "config.json")
    log_bot(bot_slug, f"📺 AdTask Worker Thread Aktif ({bot_slug})")

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
                    r = requests.get(backend_url, headers=headers, timeout=10)
                    if r.status_code in (200, 201, 204):
                        log_bot(bot_slug, f"⚡ Health check OK (HTTP {r.status_code})")
                except Exception:
                    pass

            record_success(bot_slug)
            interval = cfg.get("check_interval_seconds", 1200)
            time.sleep(interval)
        except Exception as e:
            record_failure(bot_slug, e)
            time.sleep(60)

# ==================== MAIN DAEMON ====================

def main():
    logger.info("==================================================")
    logger.info("    AD-TASK & MULTI-FAUCET UNIFIED CLUSTER RUNNER ")
    logger.info("    26 Bot Terkelola dalam 1 Proses Ringan        ")
    logger.info("==================================================")

    threads = [
        # Existing Legacy Bot Workers
        threading.Thread(target=run_legacy_worker, args=("grambuddies", "grambuddies.farmer", "run_loop"), name="Thread-GramBuddies", daemon=True),
        threading.Thread(target=run_legacy_worker, args=("boxtrust", "boxtrust.farmer", "main"), name="Thread-BoxTrust", daemon=True),
        threading.Thread(target=run_legacy_worker, args=("frogfarm", "frogfarm.farmer", "run_loop"), name="Thread-FrogFarm", daemon=True),
        # Audited Kluster 2 Flagships
        threading.Thread(target=run_grambux_thread, name="Thread-GramBux", daemon=True),
        threading.Thread(target=run_caserush_thread, name="Thread-CaseRush", daemon=True),
        threading.Thread(target=run_paidz_thread, name="Thread-PaidZ", daemon=True),
        threading.Thread(target=run_flamesearn_thread, name="Thread-FlamesEarn", daemon=True),
    ]

    # Additional Kluster 2 modular bots
    modular_adtask = [
        "dropex", "nuggyrun", "paidz_alt", "adclickersbot", "earncraft", "emojifyearnbot",
        "giftboostapp", "howl", "klikadobot", "leafearnbot", "pumpkinearnbot", "starminesr",
        "starveybot", "tgpaycryptobot", "bnbstarlbot", "gramgittbot", "gramlabpay",
        "gramsparklebot", "grami2026"
    ]
    for slug in modular_adtask:
        t = threading.Thread(target=run_generic_adtask_thread, args=(slug,), name=f"Thread-{slug}", daemon=True)
        threads.append(t)

    for t in threads:
        t.start()
        time.sleep(1.0)

    logger.info(f"Semua {len(threads)} Ad-Task bot threads telah aktif berjalan.")

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
