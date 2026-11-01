#!/usr/bin/env python3
"""
tgnative_runner.py - Unified Cluster Runner for Telegram Native & MTProto Chat Farmers
Consolidates 26 Cluster 5 Bots (Telegram Native Chat & Faucets) + 11 Existing Bots:
1. Baby Yoda (@babyyodatonbot) - Daily Galactic War & Lightsaber NFT
2. SlayLands RPG (@slaylandsbot) - Dungeon Pixel Loot & Crypto
3. Money Tree (@moneytree_game_bot) - Daily Tree Claim
4. Robot Empire (@RobotEmpireAppBot) - Re-charge & Mining
5. TON Click Robot (@TonClickRobot)
6. ClickBee Family (LTC, TRX, DOGE)
7. TRX Miner Beta (@TrxMinerBetaBot)
8. AIC Miner (@Aicminer_bot)
9. Mining GRAM (@MiningGRAM_Bot)
10. MineX Cloud (@minex_mining_bot)
11. Deep Mine (@deepmine_bot)
12. Crownville (@crownville_bot)
13. CrownMiner (Crownville Sub-miner)
14. ODRA Mining (@odra_mining_bot)
15. StarNex (@starnex_bot)
16. Bananex, Dacity, FinPilot, GmailON, Gram Store, Inside Ads, IZ Earn,
    KeepEye, LF Wallet, Lifetime Energy, NEXUM.AI, Pay Perks, QuickDigi,
    Story Corner, Super Platform, Task clicks, TOP Token, Trust updates,
    VBOT, VendoraX, Void Fleet, Xyron Wallet.

Security Features:
- Isolated Shared Telethon Session (tgnative_session.session) to prevent SQLite lock collision
- Jitter delay 3 - 7 seconds between bots to comply with Telegram FloodWait
- Fault Isolation: independent try...except per worker thread
"""

import os
import sys
import time
import glob
import json
import shutil
import random
import logging
import inspect
import asyncio
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
logger = logging.getLogger("TGNativeRunner")

AUTH_GEN_DIR = os.path.join(FARMERS_DIR, "auth_generator")
SRC_SESSION = os.path.join(AUTH_GEN_DIR, "tg_session.session")
NATIVE_SESSION = os.path.join(AUTH_GEN_DIR, "tgnative_session.session")

def ensure_native_session():
    """Mencegah SQLite lock collision dengan menyalin sesi Telethon secara mandiri"""
    try:
        if os.path.exists(SRC_SESSION):
            if not os.path.exists(NATIVE_SESSION) or os.path.getmtime(SRC_SESSION) > os.path.getmtime(NATIVE_SESSION):
                shutil.copyfile(SRC_SESSION, NATIVE_SESSION)
                logger.info("Sinkronisasi tgnative_session.session dari tg_session.session selesai.")
    except Exception as e:
        logger.warning(f"Session copy warning: {e}")

ensure_native_session()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

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


# ==================== LEGACY TELEGRAM NATIVE WORKERS ====================

LEGACY_BOTS = [
    {"name": "tonclick",    "module": "tonclick.farmer",    "func": "main_loop"},
    {"name": "clickbee",    "module": "clickbee.farmer",    "func": "main_loop"},
    {"name": "trxminer",    "module": "trxminer.farmer",    "func": "main"},
    {"name": "aicminer",    "module": "aicminer.farmer",    "func": "main_loop"},
    {"name": "mininggram",  "module": "mininggram.farmer",  "func": "run_loop"},
    {"name": "minex",       "module": "minex.farmer",       "func": "run_loop"},
    {"name": "deepmine",    "module": "deepmine.farmer",    "func": "run_farmer"},
    {"name": "crownville",  "module": "crownville.farmer",  "func": "run_farmer"},
    {"name": "crownminer",  "module": "crownminer.farmer",  "func": "run_farmer"},
    {"name": "odra",        "module": "odra.farmer",        "func": "main"},
    {"name": "starnex",     "module": "starnex.farmer",     "func": "main_loop"},
]

def legacy_bot_worker(bot_name, module_name, func_name):
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, f"🚀 Worker Legacy Native Aktif: {module_name}")

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
            if inspect.iscoroutinefunction(fn):
                asyncio.run(fn())
            else:
                fn()
            record_success(bot_name)
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(30)

TELETHON_MUTEX = threading.Lock()

async def _async_interact_bot(handle, commands, click_buttons=None):
    """Helper Telethon async untuk interaksi chat bot dengan isolasi error"""
    try:
        from telethon import TelegramClient
        client = TelegramClient(NATIVE_SESSION, API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False

        entity = await client.get_input_entity(handle)
        for cmd in commands:
            await client.send_message(entity, cmd)
            await asyncio.sleep(random.uniform(2.5, 4.5))

        if click_buttons:
            messages = await client.get_messages(entity, limit=3)
            for m in messages:
                if m.buttons:
                    for row in m.buttons:
                        for btn in row:
                            for btn_name in click_buttons:
                                if btn_name.lower() in btn.text.lower():
                                    await btn.click()
                                    await asyncio.sleep(random.uniform(2.0, 3.5))
        await client.disconnect()
        return True
    except Exception as e:
        logger.warning(f"[{handle}] Chat interaction exception: {e}")
        return False

def safe_interact_bot(handle, commands, click_buttons=None):
    """Serialize MTProto chat interactions with mutex to avoid SQLite lock collisions"""
    with TELETHON_MUTEX:
        time.sleep(random.uniform(2.0, 4.0))
        return asyncio.run(_async_interact_bot(handle, commands, click_buttons))

def run_babyyoda_thread():
    bot_name = "babyyoda"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "⚔️ Baby Yoda ($YODA NFT) Chat Worker Aktif (@babyyodatonbot)")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True) or should_skip(bot_name):
                time.sleep(60)
                continue

            ok = safe_interact_bot("babyyodatonbot", ["/start", "/claim"], ["lightsaber", "claim"])
            if ok:
                log_bot(bot_name, "✅ [Battle] Perintah interaksi Galactic War dikirim!")
                record_success(bot_name)
            else:
                record_failure(bot_name, "Interaksi bot gagal")

            time.sleep(cfg.get("check_interval_seconds", 3600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 2. SLAYLANDS RPG (@slaylandsbot) ====================

def run_slaylands_thread():
    bot_name = "slaylands"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🗡️ SlayLands RPG Chat Worker Aktif (@slaylandsbot)")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True) or should_skip(bot_name):
                time.sleep(60)
                continue

            ok = safe_interact_bot("slaylandsbot", ["/adventure", "/loot"], ["take", "claim", "attack"])
            if ok:
                log_bot(bot_name, "✅ [Dungeon] Perintah /adventure & klaim loot dikirim!")
                record_success(bot_name)
            else:
                record_failure(bot_name, "Interaksi dungeon gagal")

            time.sleep(cfg.get("check_interval_seconds", 1800))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 3. MONEY TREE (@moneytree_game_bot) ====================

def run_moneytree_thread():
    bot_name = "moneytree"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "🌳 Money Tree Chat Worker Aktif (@moneytree_game_bot)")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True) or should_skip(bot_name):
                time.sleep(60)
                continue

            ok = safe_interact_bot("moneytree_game_bot", ["/start", "/claim_tree"], ["water", "harvest"])
            if ok:
                log_bot(bot_name, "✅ [Tree] Klaim harian pohon uang dikirim!")
                record_success(bot_name)
            else:
                record_failure(bot_name, "Interaksi tree gagal")

            time.sleep(cfg.get("check_interval_seconds", 3600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== 4. ROBOT EMPIRE (@RobotEmpireAppBot) ====================

def run_robotempire_thread():
    bot_name = "robotempire"
    cfg_path = os.path.join(FARMERS_DIR, bot_name, "config.json")
    log_bot(bot_name, "⚡ Robot Empire Chat Worker Aktif (@RobotEmpireAppBot)")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True) or should_skip(bot_name):
                time.sleep(60)
                continue

            ok = safe_interact_bot("RobotEmpireAppBot", ["/start"], ["re-charge", "charge", "claim"])
            if ok:
                log_bot(bot_name, "✅ [Robot] Perintah re-charge baterai dikirim!")
                record_success(bot_name)
            else:
                record_failure(bot_name, "Interaksi robot empire gagal")

            time.sleep(cfg.get("check_interval_seconds", 3600))
        except Exception as e:
            record_failure(bot_name, e)
            time.sleep(60)

# ==================== GENERIC MODULAR TG-NATIVE WORKER ====================

def run_generic_tgnative_thread(bot_slug):
    cfg_path = os.path.join(FARMERS_DIR, bot_slug, "config.json")
    log_bot(bot_slug, f"💬 TG-Native Worker Thread Aktif ({bot_slug})")

    while True:
        try:
            if not os.path.exists(cfg_path):
                time.sleep(30)
                continue
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("enabled", True) or should_skip(bot_slug):
                time.sleep(60)
                continue

            handle = cfg.get("handle", "").lstrip("@")
            if handle:
                safe_interact_bot(handle, ["/start"])

            record_success(bot_slug)
            interval = cfg.get("check_interval_seconds", 7200)
            time.sleep(interval)
        except Exception as e:
            record_failure(bot_slug, e)
            time.sleep(60)

# ==================== MAIN DAEMON ====================

def main():
    logger.info("==================================================")
    logger.info("  TELEGRAM NATIVE & CLOUDFLARE UNIFIED RUNNER     ")
    logger.info("  37 Bot Terkelola dalam 1 Proses Ringan          ")
    logger.info("==================================================")

    threads = []

    # 1. Legacy MTProto & Native Bot Workers
    for bot in LEGACY_BOTS:
        t = threading.Thread(
            target=legacy_bot_worker,
            args=(bot["name"], bot["module"], bot["func"]),
            name=f"Thread-{bot['name']}",
            daemon=True
        )
        threads.append(t)

    # 2. Audited Kluster 5 Flagships
    threads.append(threading.Thread(target=run_babyyoda_thread, name="Thread-BabyYoda", daemon=True))
    threads.append(threading.Thread(target=run_slaylands_thread, name="Thread-SlayLands", daemon=True))
    threads.append(threading.Thread(target=run_moneytree_thread, name="Thread-MoneyTree", daemon=True))
    threads.append(threading.Thread(target=run_robotempire_thread, name="Thread-RobotEmpire", daemon=True))

    # 3. Additional Kluster 5 modular bots
    modular_native = [
        "bananex", "thedacitycoinbot", "finpilot", "gmailonbot", "gramstores", "insideads",
        "izearnbot", "keepeyeapp", "lfwalletairdropbot", "lifetimeenergy", "nexumai",
        "payperksbot", "quickdigibot", "storycornerbot", "yaojingappbot", "taskclicksbot",
        "toptokenofficialbot", "trustupdate", "vdigitalbot", "vendoraxbot", "voidfleetbot",
        "xyronwalletbot"
    ]
    for slug in modular_native:
        t = threading.Thread(target=run_generic_tgnative_thread, args=(slug,), name=f"Thread-{slug}", daemon=True)
        threads.append(t)

    for t in threads:
        t.start()
        time.sleep(1.0)

    logger.info(f"Semua {len(threads)} Native bot threads telah aktif berjalan.")

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
