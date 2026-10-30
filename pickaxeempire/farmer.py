#!/usr/bin/env python3
"""
Pickaxe Empire ($PXE) Telegram Mini-App Auto-Farmer
Features:
- Auto-claim mining rewards & storage management
- Daily check-in automation
- Auto-completion of community & link tasks
- Referral bonus claims
- Dynamic config reload & integration with auth-generator
"""

import os
import sys
import time
import json
import uuid
import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "farmer.log")
BASE_URL = "https://pxe.up.railway.app"

INSTALL_ID = str(uuid.uuid4())

def log(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
            f.flush()
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_PATH):
        log(f"ERROR: File {CONFIG_PATH} tidak ditemukan!")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_headers(cfg):
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://app.pickaxeempire.com",
        "Referer": "https://app.pickaxeempire.com/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "x-telegram-init-data": cfg.get("init_data", ""),
        "x-tg-platform": "android",
        "x-install-id": INSTALL_ID
    }

def fetch_me(cfg):
    url = f"{BASE_URL}/api/me"
    try:
        r = requests.post(url, headers=get_headers(cfg), json={}, timeout=15)
        if r.status_code == 200:
            return r.json()
        log(f"Gagal mengambil info akun (HTTP {r.status_code}): {r.text[:150]}")
    except Exception as e:
        log(f"Error fetch_me: {e}")
    return None

def claim_mining(cfg):
    url = f"{BASE_URL}/api/claim"
    try:
        r = requests.post(url, headers=get_headers(cfg), json={}, timeout=15)
        data = r.json()
        if r.status_code == 200:
            claimed = data.get("claimed", 0)
            in_app = data.get("inApp", 0)
            lvl = data.get("level", 1)
            log("=" * 50)
            log(">> KLAIM MINING PXE BERHASIL! <<")
            log(f"Reward Diklaim : +{claimed:,.2f} PXE")
            log(f"Saldo Total    : {in_app:,.2f} PXE (Level {lvl})")
            log("=" * 50)
            return True, data
        else:
            err = data.get("error", "")
            if "ancient pass" in err.lower():
                log(f"ℹ️ Klaim ditunda: {err}")
            elif "not full" in err.lower() or "nothing" in err.lower():
                log("ℹ️ Mining belum terakumulasi cukup untuk diklaim.")
            else:
                log(f"Respon klaim (HTTP {r.status_code}): {err}")
            return False, data
    except Exception as e:
        log(f"Error claim_mining: {e}")
        return False, str(e)

def claim_checkin(cfg):
    if not cfg.get("auto_checkin", True):
        return
    url = f"{BASE_URL}/api/checkin"
    try:
        r = requests.post(url, headers=get_headers(cfg), json={}, timeout=15)
        data = r.json()
        if r.status_code == 200:
            reward = data.get("checkinReward", 0)
            streak = data.get("checkin", {}).get("streak", 1)
            log(f">> DAILY CHECK-IN BERHASIL! +{reward} PXE (Streak: {streak} hari) <<")
        elif r.status_code == 400 and "already checked in" in data.get("error", "").lower():
            pass # Sudah check-in hari ini, normal
        else:
            log(f"[Check-in] Status: {r.status_code} - {data.get('error', data)}")
    except Exception as e:
        log(f"[Check-in] Error: {e}")

def process_tasks(cfg, me_data):
    if not cfg.get("auto_tasks", True):
        return
    if not me_data:
        return

    task_status_map = {t["id"]: t["status"] for t in me_data.get("tasks", [])}
    task_defs = me_data.get("taskDefs", [])

    for t in task_defs:
        tid = t.get("id")
        kind = t.get("kind")
        status = task_status_map.get(tid, "todo")
        title = t.get("title", tid)
        reward = t.get("reward", 0)
        wait_sec = t.get("wait", 0)

        # Hanya proses task link dan channel yang belum selesai
        if status == "todo" and kind in ["link", "channel"]:
            log(f"Memproses Task: '{title}' (+{reward} PXE)...")
            try:
                # 1. Start task
                s_res = requests.post(f"{BASE_URL}/api/tasks/{tid}/start", headers=get_headers(cfg), json={}, timeout=10)
                if s_res.status_code == 200:
                    time_to_wait = max(wait_sec, 2)
                    time.sleep(time_to_wait + 1)
                    # 2. Claim task
                    c_res = requests.post(f"{BASE_URL}/api/tasks/{tid}/claim", headers=get_headers(cfg), json={}, timeout=10)
                    if c_res.status_code == 200 and c_res.json().get("taskReward"):
                        log(f"✅ >> BERHASIL KLAIM TASK '{title}'! +{reward} PXE <<")
            except Exception as e:
                log(f"Error memproses task {tid}: {e}")

def claim_referrals(cfg):
    url = f"{BASE_URL}/api/referrals/claim"
    try:
        r = requests.post(url, headers=get_headers(cfg), json={}, timeout=10)
        if r.status_code == 200 and r.json().get("claimed"):
            claimed = r.json().get("claimed")
            log(f"🎉 >> BERHASIL KLAIM KOMISI REFERRAL: +{claimed:,.2f} PXE <<")
    except Exception:
        pass

def run_farmer_cycle(cfg):
    me = fetch_me(cfg)
    if not me:
        return

    profile = me.get("profile", {})
    in_app = me.get("inApp", 0)
    unclaimed = me.get("unclaimed", 0)
    level = me.get("level", 1)
    speed = me.get("speed", 0.2)
    per_day = me.get("perDay", 5)
    storage_cap = me.get("storageCap", 5)
    pass_info = me.get("pass", {})
    pass_active = pass_info.get("active", False)
    price_usd = me.get("priceUsd", 0.0083)
    checkin = me.get("checkin", {})

    log("=" * 50)
    log(f"User          : {profile.get('name', 'User')} (@{profile.get('username', '-')})")
    log(f"Saldo PXE     : {in_app:,.2f} PXE (${in_app * price_usd:.2f})")
    log(f"Unclaimed     : {unclaimed:,.2f} / {storage_cap} PXE (Speed: {speed} PXE/jam, +{per_day}/hari)")
    log(f"Level         : Level {level}")
    log(f"Ancient Pass  : {'🟢 AKTIF' if pass_active else '🟡 Belum Mint (0.1 TON)'}")
    log(f"Check-in      : Streak {checkin.get('streak', 0)} hari (Hari ini: {'Sudah' if checkin.get('checkedToday') else 'Belum'})")
    log(f"Harga PXE     : ${price_usd:.6f} USD")
    log("=" * 50)

    # 1. Auto Daily Check-in
    claim_checkin(cfg)

    # 2. Auto Tasks
    process_tasks(cfg, me)

    # 3. Auto Claim Mining
    claim_mining(cfg)

    # 4. Auto Claim Referral
    claim_referrals(cfg)

def main():
    log("=== Pickaxe Empire ($PXE) Auto-Farmer Started ===")
    cfg = load_config()

    if "--once" in sys.argv:
        log("Mode: One-Shot Manual Test")
        run_farmer_cycle(cfg)
        return

    interval = cfg.get("check_interval_seconds", 600)
    while True:
        try:
            cfg = load_config()
            interval = cfg.get("check_interval_seconds", 600)
            run_farmer_cycle(cfg)
            log(f"Tidur selama {interval} detik (~{int(interval/60)} menit)...")
            time.sleep(interval)
        except KeyboardInterrupt:
            log("Farmer dihentikan oleh pengguna.")
            break
        except Exception as e:
            log(f"Unexpected error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
