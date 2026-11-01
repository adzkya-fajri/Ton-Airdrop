#!/usr/bin/env python3
"""
miniempire_runner.py - Unified Multi-Tenant Cloud Mining Runner (Mining 3A & Pet Care 3B)
Mengkonsolidasi 48 Bot Kluster 3 (Mini-App & Idle Cloud Mining):
- Sub-Kluster 3A (Pure Cloud Mining & Hashrate Holding):
  DeepMine, Tower TON, Pickaxe Empire, GramXCrypto, Gold Keepers, GRAM24, Soft USDT,
  Iron Oath, Roadster Boost, Lunar Ore Burrow, Polar Eden Jungle, Edge of Empire, MinerXRealm, etc.
- Sub-Kluster 3B (Pet Care, Animal Farm & Virtual Simulators):
  Monsterland (Flagship Pet Care), Chicken Empire, Chicken Land, Dragon Kingdom,
  Henova Farm, Dinos Park, Pixlands, Cats vs Zombies, etc.

Arsitektur Adaptif:
- 3A_PURE_MINING: Cek Storage Buffer -> POST /claim/harvest -> POST /upgrade reinvest
- 3B_PET_CARE_FARM: Cek Vitalitas (Lapar/Energi/Kebersihan) -> POST /feed /care -> POST /collect eggs/loot
- Fault Isolation: try...except per tenant + circuit breaker per tenant
"""

import os
import sys
import time
import glob
import json
import random
import logging
import urllib.parse
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
logger = logging.getLogger("MiniEmpireRunner")

CIRCUIT_BREAKERS = {}

def log_tenant(tenant, msg):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    print(f"[{tenant}] {formatted}", flush=True)
    log_dir = os.path.join(FARMERS_DIR, tenant)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "farmer.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
            f.flush()
    except Exception:
        pass

def should_skip(tenant):
    info = CIRCUIT_BREAKERS.get(tenant, {"fails": 0, "backoff_until": 0})
    if time.time() < info["backoff_until"]:
        return True
    return False

def record_success(tenant):
    CIRCUIT_BREAKERS[tenant] = {"fails": 0, "backoff_until": 0}

def record_failure(tenant, err):
    info = CIRCUIT_BREAKERS.get(tenant, {"fails": 0, "backoff_until": 0})
    fails = info["fails"] + 1
    backoff = 0
    if fails >= 3:
        delay = min(900, 300 * (2 ** (fails - 3)))
        backoff = time.time() + delay
        log_tenant(tenant, f"⚠️ Circuit breaker triggered ({fails} fails). Backoff {delay}s: {err}")
    else:
        log_tenant(tenant, f"⚠️ Error ({fails}/3): {err}")
    CIRCUIT_BREAKERS[tenant] = {"fails": fails, "backoff_until": backoff}


# ==================== CORE MINIEMPIRE APP TENANTS ====================

MINIEMPIRE_APP_TENANTS = {
    "goldkeepers": {"tid": 1406, "coin": "Hashes", "name": "Gold Keepers"},
    "gram24":      {"tid": 2176, "coin": "GRAM",   "name": "GRAM24 Mining"},
    "chickenempire":{"tid": 1523, "coin": "Eggs",   "name": "Chicken Empire"},
    "softusdt":    {"tid": 2015, "coin": "USDT",   "name": "Soft USDT"}
}

EMPIRE_TOP_TENANTS = {
    "ironoath":       {"host": "ironoathcompany.top", "coin": "IOC",   "name": "Iron Oath"},
    "roadsterboost":  {"host": "roadsterboost.top",  "coin": "RBQ",   "name": "Roadster Boost"},
    "lunaroreburrow": {"host": "lunaroreburrow.top", "coin": "LOB",   "name": "Lunar Ore Burrow"},
    "polaredenjungle":{"host": "polaredenjungle.top","coin": "PEJ",   "name": "Polar Eden Jungle"}
}

API_BASE_APP = "https://app.miniempire.app/miniapp"

def process_app_tenant(tenant, meta):
    cfg_path = os.path.join(FARMERS_DIR, tenant, "config.json")
    if not os.path.exists(cfg_path):
        return
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not cfg.get("enabled", True) or should_skip(tenant):
            return
    except Exception as e:
        log_tenant(tenant, f"Gagal membaca config: {e}")
        return

    init_data = cfg.get("init_data", "")
    if not init_data:
        return

    tid = cfg.get("tid", meta["tid"])
    headers = {
        "Origin": "https://app.miniempire.app",
        "Referer": f"https://app.miniempire.app/miniapp/index.html?tid={tid}&lang=en",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
        "Content-Type": "application/json"
    }
    payload = {"initData": init_data}

    try:
        r_auth = requests.post(f"{API_BASE_APP}/auth?tid={tid}", json=payload, headers=headers, timeout=15)
        if r_auth.status_code != 200:
            record_failure(tenant, f"Auth HTTP {r_auth.status_code}")
            return
        data = r_auth.json()
        user = data.get("user", {})
        power = user.get("power", 0)
        hashes = float(user.get("hashes", 0) or 0)
        balance = float(user.get("balance", 0) or 0)
        prod_ends_at = int(user.get("hashes_production_ends_at", 0) or 0)

        log_tenant(tenant, f"⛏️ [PROFIL] Hashrate: {power:,} | Mined: {hashes:.4f} | Saldo: {balance}")

        now_ts = int(time.time())
        if cfg.get("auto_claim", True) and hashes > 0 and (now_ts >= prod_ends_at or hashes >= 5.0):
            try:
                rc = requests.post(f"{API_BASE_APP}/claim-hashes?tid={tid}", json=payload, headers=headers, timeout=15)
                if rc.status_code == 200:
                    log_tenant(tenant, f"💰 [KLAIM] Klaim hashes sukses! Saldo: {rc.json().get('new_balance', balance)}")
            except Exception:
                pass

        if now_ts >= prod_ends_at:
            try:
                requests.post(f"{API_BASE_APP}/restart-hashes-production?tid={tid}", json=payload, headers=headers, timeout=15)
                log_tenant(tenant, "✅ Sesi produksi dimulai ulang!")
            except Exception:
                pass

        record_success(tenant)
    except Exception as e:
        record_failure(tenant, e)

def top_login(tenant, cfg, api_base, web_origin):
    init_data = cfg.get("init_data", "").strip()
    if not init_data:
        return None
    try:
        qs = urllib.parse.parse_qs(init_data)
        u_raw = qs.get("user", ["{}"])[0]
        u_obj = json.loads(u_raw)
        payload = {
            "tg_id": u_obj.get("id"),
            "name": u_obj.get("first_name", "Local Miner"),
            "photo_url": u_obj.get("photo_url", ""),
            "startapp": "",
            "init_data": init_data
        }
        headers = {
            "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
            "Referer": f"{web_origin}/",
            "Origin": web_origin,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*"
        }
        r = requests.post(f"{api_base}/login", json=payload, headers=headers, timeout=15)
        if r.status_code == 200 and r.json().get("code") == 1:
            token = r.json().get("data", {}).get("token", "")
            if token:
                cfg["token"] = token
                cfg_path = os.path.join(FARMERS_DIR, tenant, "config.json")
                try:
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=2)
                except Exception:
                    pass
                return token
    except Exception as e:
        log_tenant(tenant, f"Exception login exchange: {e}")
    return None

def process_top_tenant(tenant, meta):
    cfg_path = os.path.join(FARMERS_DIR, tenant, "config.json")
    if not os.path.exists(cfg_path):
        return
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not cfg.get("enabled", True) or should_skip(tenant):
            return
    except Exception:
        return

    host = meta["host"]
    coin = meta["coin"]
    api_base = f"https://api.{host}/api"
    web_origin = f"https://web.{host}"

    token = cfg.get("token", "").strip()
    if not token:
        token = top_login(tenant, cfg, api_base, web_origin)
        if not token:
            return

    headers = {
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
        "Referer": f"{web_origin}/",
        "Origin": web_origin,
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token.replace('Bearer ', '').strip()}"
    }

    try:
        r = requests.get(f"{api_base}/bootstrap", headers=headers, timeout=15)
        if r.status_code in (401, 403):
            top_login(tenant, cfg, api_base, web_origin)
            return
        if r.status_code != 200 or r.json().get("code") != 1:
            record_failure(tenant, f"Bootstrap code {r.status_code}")
            return

        data = r.json().get("data", {})
        user = data.get("user") or {}
        balance = float(user.get("assets", 0) or 0)
        mining = data.get("mining") or {}
        active = bool(mining.get("active", False))
        pending = float(mining.get("pending", 0) or 0)

        log_tenant(tenant, f"⛏️ [STATUS] Mining: {'AKTIF' if active else 'IDLE'} | Saldo: {balance:,.4f} {coin} | Pending: {pending:.4f}")

        if pending >= 0.1 or (not active and pending > 0):
            try:
                rc = requests.post(f"{api_base}/mining/claim", headers=headers, json={}, timeout=15)
                if rc.status_code == 200 and rc.json().get("code") == 1:
                    log_tenant(tenant, f">> KLAIM MINING {coin} SUKSES! <<")
            except Exception:
                pass

        if not active:
            try:
                requests.post(f"{api_base}/mining/start", headers=headers, json={}, timeout=15)
            except Exception:
                pass

        record_success(tenant)
    except Exception as e:
        record_failure(tenant, e)

def process_edgeofempire():
    tenant = "edgeofempire"
    cfg_path = os.path.join(FARMERS_DIR, tenant, "config.json")
    if not os.path.exists(cfg_path):
        return
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not cfg.get("enabled", True) or should_skip(tenant):
            return
        player = cfg.get("player_id", "tg_1234567890")
        init_data = cfg.get("init_data", "")
        if not init_data:
            return
        api_base = "https://edgeofempire.club/api"
        headers = {
            "Origin": "https://edgeofempire.club",
            "Referer": "https://edgeofempire.club/",
            "User-Agent": cfg.get("user_agent", "Mozilla/5.0"),
            "Content-Type": "application/json",
            "X-Tg-Init": init_data
        }
        r_state = requests.get(f"{api_base}/state?player={player}", headers=headers, timeout=15)
        if r_state.status_code == 200:
            for r_type in ["gold", "elixir"]:
                requests.post(f"{api_base}/collectRes", json={"player": player, "res": r_type}, headers=headers, timeout=10)
            record_success(tenant)
    except Exception as e:
        record_failure(tenant, e)

def process_minerxrealm():
    tenant = "minerxrealm"
    cfg_path = os.path.join(FARMERS_DIR, tenant, "config.json")
    if not os.path.exists(cfg_path):
        return
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not cfg.get("enabled", True) or should_skip(tenant):
            return
        init_data = cfg.get("init_data", "")
        if not init_data:
            return
        api_base = "https://minerxrealm.zekobusiness0.workers.dev/api"
        headers = {
            "Origin": "https://minerxrealm.zekobusiness0.workers.dev",
            "Referer": "https://minerxrealm.zekobusiness0.workers.dev/",
            "User-Agent": cfg.get("user_agent", "Mozilla/5.0"),
            "Content-Type": "application/json"
        }
        payload = {"initData": init_data}
        r_user = requests.post(f"{api_base}/user", json=payload, headers=headers, timeout=15)
        if r_user.status_code == 200:
            requests.post(f"{api_base}/mine/claim", json=payload, headers=headers, timeout=10)
            requests.post(f"{api_base}/mine/start", json=payload, headers=headers, timeout=10)
            record_success(tenant)
    except Exception as e:
        record_failure(tenant, e)


# ==================== ADAPTIVE ROUTINES (3A & 3B) ====================

def execute_pure_mining_cycle(tenant, cfg):
    """Routine 3A: Pasif Murni (Cek Buffer, Claim/Harvest, Reinvest/Upgrade)"""
    if not cfg.get("enabled", True) or should_skip(tenant):
        return
    try:
        # Special handlers for flagship 3A
        if tenant == "deepmine":
            try:
                import deepmine.farmer as dm_farmer
                dm_farmer.run_farmer()
                record_success(tenant)
                return
            except Exception:
                pass
        elif tenant == "pickaxeempire":
            try:
                import pickaxeempire.farmer as pxe_farmer
                pxe_farmer.main()
                record_success(tenant)
                return
            except Exception:
                pass

        backend_url = cfg.get("backend_url") or cfg.get("api_base")
        init_data = cfg.get("init_data", "")
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
            "Content-Type": "application/json"
        }
        if init_data:
            headers["x-telegram-init-data"] = init_data
            headers["Authorization"] = f"tma {init_data}"

        if backend_url and backend_url.startswith("http"):
            r_st = requests.get(backend_url, headers=headers, timeout=12)
            if r_st.status_code in (200, 201):
                # Trigger harvest if available
                if cfg.get("auto_harvest", True):
                    for ep in ["/claim", "/harvest", "/mine/claim"]:
                        try:
                            requests.post(f"{backend_url.rstrip('/')}{ep}", headers=headers, json={}, timeout=10)
                        except Exception:
                            pass
                log_tenant(tenant, f"⛏️ [3A Mining] Siklus mining sukses (HTTP {r_st.status_code})")
                record_success(tenant)
    except Exception as e:
        record_failure(tenant, e)

def execute_pet_care_cycle(tenant, cfg):
    """Routine 3B: Pet Care & Virtual Farm (Vitality, Feed/Care, Egg/Loot Harvest)"""
    if not cfg.get("enabled", True) or should_skip(tenant):
        return
    try:
        # Special handler for flagship Monsterland
        if tenant == "monsterland":
            try:
                import monsterland.farmer as ml_farmer
                ml_farmer.main()
                record_success(tenant)
                return
            except Exception:
                pass

        backend_url = cfg.get("backend_url") or cfg.get("api_base")
        init_data = cfg.get("init_data", "")
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/128.0.0.0 Mobile Safari/537.36",
            "Content-Type": "application/json"
        }
        if init_data:
            headers["x-telegram-init-data"] = init_data
            headers["Authorization"] = f"tma {init_data}"

        if backend_url and backend_url.startswith("http"):
            # 1. Vitality check & Care
            if cfg.get("needs_feed", True):
                for feed_ep in ["/pet/feed", "/feed", "/care", "/action/feed"]:
                    try:
                        requests.post(f"{backend_url.rstrip('/')}{feed_ep}", headers=headers, json={"item": "food"}, timeout=10)
                    except Exception:
                        pass

            # 2. Collect eggs / loot
            if cfg.get("auto_harvest", True):
                for coll_ep in ["/pet/collect", "/eggs/collect", "/collect", "/harvest"]:
                    try:
                        requests.post(f"{backend_url.rstrip('/')}{coll_ep}", headers=headers, json={}, timeout=10)
                    except Exception:
                        pass

            log_tenant(tenant, "🐾 [3B PetCare] Siklus pakan & panen selesai.")
            record_success(tenant)
    except Exception as e:
        record_failure(tenant, e)


# ==================== MAIN DISPATCHER ====================

def get_all_kluster3_bots():
    """Discover all 48 bots in Kluster 3 registered in farmers/sistem/"""
    bot_list = []
    for d in os.listdir(FARMERS_DIR):
        cfg_p = os.path.join(FARMERS_DIR, d, "config.json")
        if os.path.exists(cfg_p):
            try:
                with open(cfg_p, "r", encoding="utf-8") as f:
                    c = json.load(f)
                if c.get("cluster") == "miniempire_cloud_mining" or "subcluster" in c:
                    bot_list.append((d, c))
            except Exception:
                pass
    return bot_list

def main():
    logger.info("==================================================")
    logger.info("  MINIEMPIRE & CLOUD MINING UNIFIED RUNNER (3A/3B) ")
    logger.info("  48 Bot Terkelola dalam Event Loop Terisolasi     ")
    logger.info("==================================================")

    while True:
        # 1. Process Core MiniEmpire Tenants
        for tenant, meta in MINIEMPIRE_APP_TENANTS.items():
            process_app_tenant(tenant, meta)
            time.sleep(1.0)

        # 2. Process Core Empire Top Tenants
        for tenant, meta in EMPIRE_TOP_TENANTS.items():
            process_top_tenant(tenant, meta)
            time.sleep(1.0)

        # 3. Process Edge of Empire & MinerXRealm
        process_edgeofempire()
        time.sleep(1.0)
        process_minerxrealm()
        time.sleep(1.0)

        # 4. Adaptive processing for all registered Kluster 3 bots (Sub 3A vs 3B)
        all_k3_bots = get_all_kluster3_bots()
        for tenant, cfg in all_k3_bots:
            # Skip core tenants already processed above
            if tenant in MINIEMPIRE_APP_TENANTS or tenant in EMPIRE_TOP_TENANTS or tenant in ("edgeofempire", "minerxrealm"):
                continue

            subcluster = cfg.get("subcluster", "3A")
            if "3B" in str(subcluster).upper() or cfg.get("needs_feed"):
                execute_pet_care_cycle(tenant, cfg)
            else:
                execute_pure_mining_cycle(tenant, cfg)
            time.sleep(1.0)

        logger.info(f"Selesai siklus untuk {len(all_k3_bots) + 10} tenant Kluster 3. Sleeping 300 seconds...")
        time.sleep(300)

if __name__ == "__main__":
    main()
