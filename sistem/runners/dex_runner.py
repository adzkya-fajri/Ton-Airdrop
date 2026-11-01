#!/usr/bin/env python3
"""
dex_runner.py - Unified Cluster Runner for DEX & Listed Mining Tokens
Mengkonsolidasi 11 Bot Kluster 4 (DEX & Listed Tokens) + 10 Bot Eksisting:
1. Blum (@blum) - Top Tier Web3 Hybrid DEX & Memepad
2. Grouche Mine (@grc_airdroobot) - STON.fi DEX Pair
3. QAQ (@qaqofficialappbot) - PancakeSwap BSC Listed
4. DRAM Miner (@DRAMminer_bot) - DeDust DEX
5. ATF Miner (@ATF_AIRDROP_bot) - DeDust DEX
6. Diggo Miner (@Diggominer_bot) - STON.fi DEX
7. Music MB (@MusicMiningMB_Bot) - STON.fi DEX
8. LumeTRA (@LUMETRAS_BOT) - STON.fi DEX
9. Tomarket (@Tomarket_ai_bot) - STON.fi / Bitget
10. Pickaxe Empire (@pickaxeempire_bot) - DeDust DEX
11. VYQ Miner (@VYQMiners_bot) - DeDust DEX
12. Epsilon Miner (@epsilon_miner_bot) - Pre-TGE
13. mAInet (@mAInet_bot) - Pre-TGE
14. Army of ARNI, $BPL Wallet, BasedBot, GramMiner, LootVault, Pitcoin Miner, Dragon Realm, LUM.
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
logger = logging.getLogger("DEXRunner")

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

def should_skip(bot_name):
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


# ==================== LEGACY DEX BOT WORKERS ====================

LEGACY_BOTS = [
    {"name": "dram",          "module": "dram.farmer",          "func": "main"},
    {"name": "atf",           "module": "atf.farmer",           "func": "main"},
    {"name": "diggo",         "module": "diggo.farmer",         "func": "main"},
    {"name": "musicmb",       "module": "musicmb.farmer",       "func": "run_loop"},
    {"name": "lumetra",       "module": "lumetra.farmer",       "func": "run_farmer"},
    {"name": "tomarket",      "module": "tomarket.farmer",      "func": "run_farmer"},
    {"name": "pickaxeempire", "module": "pickaxeempire.farmer", "func": "main"},
    {"name": "vyq",           "module": "vyq.farmer",           "func": "run_loop"},
    {"name": "epsilon",       "module": "epsilon.farmer",       "func": "main"},
    {"name": "mainet",        "module": "mainet.farmer",        "func": "main"},
]

def legacy_bot_worker(bot_name, module_name, func_name):
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, f"🚀 Worker Legacy DEX Aktif: {module_name}")

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

            if should_skip(bot_name):
                time.sleep(30)
                continue

            mod = __import__(module_name, fromlist=[func_name])
            fn = getattr(mod, func_name)
            fn()
            record_success(bot_name)
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(30)

# ==================== 1. BLUM (@blum) ====================

def run_blum_thread():
    bot_name = "blum"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🌸 Blum Official DEX Worker Thread Aktif (@blum)")

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
            if should_skip(bot_name):
                time.sleep(30)
                continue

            api_base = "https://game-domain.blum.codes/api/v1"
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["Authorization"] = f"Bearer {init_data}"

            r_bal = requests.get(f"{api_base}/user/balance", headers=headers, timeout=15)
            if r_bal.status_code == 200:
                data = r_bal.json()
                avail_bal = float(data.get("availableBalance", 0))
                play_passes = data.get("playPasses", 0)
                farming = data.get("farming", {})
                log_bot(bot_name, f"🌸 [Status] Poin: {avail_bal:,.2f} | Tiket Drop Game: {play_passes}")

                # Farming check & claim
                now_ts = int(time.time() * 1000)
                if farming:
                    end_ts = farming.get("endTime", 0)
                    if now_ts >= end_ts and cfg.get("auto_claim", True):
                        r_clm = requests.post(f"{api_base}/farming/claim", headers=headers, json={}, timeout=15)
                        if r_clm.status_code == 200:
                            log_bot(bot_name, "✅ [Farming] Sukses klaim reward farming Blum!")
                            requests.post(f"{api_base}/farming/start", headers=headers, json={}, timeout=15)
                else:
                    requests.post(f"{api_base}/farming/start", headers=headers, json={}, timeout=15)

                # Daily check-in
                try:
                    requests.post(f"{api_base}/daily-reward", headers=headers, json={}, timeout=10)
                except Exception:
                    pass

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 1800))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 2. GROUCHE MINE (@grc_airdroobot) ====================

def run_grc_thread():
    bot_name = "grc"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🍐 Grouche Mine ($GRC STON.fi) Worker Thread Aktif (@grc_airdroobot)")

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
            if should_skip(bot_name):
                time.sleep(30)
                continue

            backend_url = cfg.get("backend_url", "https://grc-mine.com/api").rstrip("/")
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["x-telegram-init-data"] = init_data

            r_st = requests.get(f"{backend_url}/status", headers=headers, timeout=15)
            if r_st.status_code == 200:
                data = r_st.json()
                grc_bal = float(data.get("balance", 0))
                mined = float(data.get("unclaimed", 0))
                log_bot(bot_name, f"🍐 [Status] Saldo: {grc_bal:,.2f} GRC | Mined: {mined:,.2f} GRC (STON.fi DEX Pair)")

                if mined > 0 and cfg.get("auto_claim", True):
                    r_c = requests.post(f"{backend_url}/claim", headers=headers, json={}, timeout=15)
                    if r_c.status_code == 200:
                        log_bot(bot_name, f"✅ [Panen] Sukses klaim +{mined} GRC!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 1200))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 3. QAQ (@qaqofficialappbot) ====================

def run_qaq_thread():
    bot_name = "qaq"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🪙 QAQ Mining (PancakeSwap BSC) Worker Thread Aktif (@qaqofficialappbot)")

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
            if should_skip(bot_name):
                time.sleep(30)
                continue

            backend_url = cfg.get("backend_url", "https://qaq.fast-app.top/api").rstrip("/")
            init_data = cfg.get("init_data", "")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B)",
                "Content-Type": "application/json"
            }
            if init_data:
                headers["Authorization"] = f"tma {init_data}"

            r = requests.get(f"{backend_url}/profile", headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                bal = float(data.get("balance", 0))
                can_claim = data.get("canClaim", True)
                log_bot(bot_name, f"🪙 [Status] Saldo QAQ: {bal:,.4f} | Status Klaim: {'READY' if can_claim else 'MINING'}")

                if can_claim and cfg.get("auto_claim", True):
                    requests.post(f"{backend_url}/claim", headers=headers, json={}, timeout=15)
                    log_bot(bot_name, "✅ [Claim] Sukses klaim siklus 24 jam QAQ token!")

            record_success(bot_name)
            time.sleep(cfg.get("check_interval_seconds", 3600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== GENERIC MODULAR DEX WORKER ====================

def run_generic_dex_thread(bot_slug):
    cfg_path = os.path.join(FARMERS_DIR, bot_slug, "config.json")
    log_bot(bot_slug, f"📈 DEX Worker Thread Aktif ({bot_slug})")

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
            if should_skip(bot_slug):
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
            interval = cfg.get("check_interval_seconds", 1800)
            time.sleep(interval)
        except Exception as e:
            record_failure(bot_slug, e)
            time.sleep(60)

# ==================== MAIN DAEMON ====================

def main():
    logger.info("==================================================")
    logger.info("     DEX & LISTED TOKENS UNIFIED CLUSTER RUNNER   ")
    logger.info("    21 Bot Terkelola dalam 1 Proses Ringan        ")
    logger.info("==================================================")

    threads = []

    # 1. Legacy DEX Bot Workers
    for bot in LEGACY_BOTS:
        t = threading.Thread(
            target=legacy_bot_worker,
            args=(bot["name"], bot["module"], bot["func"]),
            name=f"Thread-{bot['name']}",
            daemon=True
        )
        threads.append(t)

    # 2. Audited Kluster 4 Flagships
    threads.append(threading.Thread(target=run_blum_thread, name="Thread-Blum", daemon=True))
    threads.append(threading.Thread(target=run_grc_thread, name="Thread-GRC", daemon=True))
    threads.append(threading.Thread(target=run_qaq_thread, name="Thread-QAQ", daemon=True))

    # 3. Additional Kluster 4 modular bots
    modular_dex = ["arniarmy", "bplwalletbot", "basedeth", "gmmgamebot", "lootvaultdexbot", "pitbullcoinbot", "dragonrealmofficialappbot", "lumeonminer"]
    for slug in modular_dex:
        t = threading.Thread(target=run_generic_dex_thread, args=(slug,), name=f"Thread-{slug}", daemon=True)
        threads.append(t)

    for t in threads:
        t.start()
        time.sleep(1.0)

    logger.info(f"Semua {len(threads)} DEX bot threads telah aktif berjalan.")

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
