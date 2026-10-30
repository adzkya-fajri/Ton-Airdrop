#!/usr/bin/env python3
"""
ODRA Mining Telegram Mini-App Auto-Farmer (odra.onrender.com)
Automasi:
1. Auto-collect mining balance (/api/collect)
2. Daily Streak Check-in (/api/checkin)
3. Auto-Tapping (/api/tap) jika ada tapsLeft
4. Auto-Task completion & claim (/api/taskstart, /api/taskclaim)
5. Auto-Claim referral/team commission (/api/claim)
6. Tracking metric saldo ODRA & nilai USD
"""

import os
import sys
import time
import json
import random
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
BASE_URL = "https://odra.onrender.com"

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
            f.flush()
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_FILE):
        log(f"ERROR: File {CONFIG_FILE} tidak ditemukan!")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_headers(cfg):
    return {
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"),
        "Content-Type": "application/json",
        "Accept": "*/*"
    }

def api(cfg, endpoint, payload=None):
    init_data = cfg.get("init_data", "").strip()
    if not init_data:
        return {"error": "no_init_data"}

    url = f"{BASE_URL}/api/{endpoint}"
    headers = get_headers(cfg)
    body = {"initData": init_data}
    if payload and isinstance(payload, dict):
        body.update(payload)

    try:
        res = requests.post(url, headers=headers, json=body, timeout=15)
        if res.status_code == 200:
            try:
                return res.json()
            except Exception:
                return {"error": "json_parse_error"}
        elif res.status_code == 401:
            log(">> Sesi ODRA expired (HTTP 401: auth) - butuh update init_data di config.json <<")
            return {"error": "auth"}
        else:
            return {"error": f"http_{res.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def auto_collect(cfg, state):
    mined = float(state.get("mined", 0) or 0)
    if mined <= 0:
        return False

    log(f"Mendeteksi mined balance: {mined:.7f} ODRA. Mengirim request /api/collect...")
    res = api(cfg, "collect")
    if not res.get("error"):
        new_bal = float(res.get("bal", 0) or 0)
        log("=" * 50)
        log(f">> KLAIM MINING ODRA BERHASIL! +{mined:.6f} ODRA <<")
        log(f"Saldo Baru: {new_bal:.4f} ODRA")
        log("=" * 50)
        return True
    else:
        log(f">> Gagal collect mined ODRA: {res.get('error')} <<")
        return False

def auto_checkin(cfg, state):
    ci = state.get("ci", {})
    if isinstance(ci, dict) and not ci.get("done", False):
        day = ci.get("day", 1)
        log(f"Melakukan Daily Check-in ODRA (Hari ke-{day})...")
        res = api(cfg, "checkin")
        if not res.get("error"):
            reward = res.get("reward", 0)
            log(f">> CHECK-IN ODRA BERHASIL! (+{reward} ODRA) <<")
            return True
        else:
            log(f">> Status check-in ODRA: {res.get('error')} <<")
    return False

def auto_tap(cfg, state):
    taps_left = int(state.get("tapsLeft", 0) or 0)
    if taps_left <= 0:
        return

    # Tap secukupnya per siklus (max 30 tap) agar natural
    batch = min(taps_left, 30)
    log(f"Tersedia {taps_left} jatah tap. Menjalankan auto-tap {batch}x...")
    success = 0
    for _ in range(batch):
        r = api(cfg, "tap")
        if not r.get("error"):
            success += 1
        elif r.get("error") == "limit":
            break
        time.sleep(0.2)
    if success > 0:
        log(f">> Selesai mengeksekusi {success}x tap ODRA! <<")

def auto_tasks(cfg, state):
    tasks_done = set(state.get("tasks", []))
    tasks_started = set(state.get("tstarted", []))
    cfg_tasks = state.get("cfg", {}).get("tasks", [])

    if not isinstance(cfg_tasks, list):
        return

    for t in cfg_tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        title = t.get("title") or tid
        reward = t.get("r", 0)

        # STRICT SAFETY: Skip any hold/deposit task
        if "hold" in str(tid).lower() or "deposit" in str(tid).lower() or "buy" in str(tid).lower():
            continue

        if tid not in tasks_done:
            if tid not in tasks_started and t.get("wait"):
                api(cfg, "taskstart", {"id": tid})
                time.sleep(1)

            res = api(cfg, "taskclaim", {"id": tid})
            if not res.get("error"):
                rew = res.get("reward", reward)
                log(f">> BERHASIL KLAIM TASK ODRA '{title}' (+{rew} ODRA)! <<")
            else:
                log(f">> Status task ODRA '{title}': {res.get('error')} <<")
            time.sleep(1)

def auto_claim_pool(cfg, state):
    pool = float(state.get("pool", 0) or 0)
    if pool > 0:
        log(f"Mendeteksi komisi team/referral: {pool:.2f} ODRA. Mengklaim...")
        res = api(cfg, "claim")
        if not res.get("error"):
            log(f">> BERHASIL KLAIM KOMISI TEAM ODRA! (+{pool:.2f} ODRA) <<")

def run_cycle(cfg):
    state = api(cfg, "state")
    if state.get("error"):
        log(f">> Error mengambil state ODRA: {state.get('error')} <<")
        return False

    bal = float(state.get("bal", 0) or 0)
    mined = float(state.get("mined", 0) or 0)
    lvl = state.get("lvl", 0)
    speed = float(state.get("speed", 0) or 0)
    wallet = state.get("wallet") or "Not connected"
    taps_left = state.get("tapsLeft", 0)

    log("=" * 50)
    log(f"ODRA Mining Status | Lvl {lvl} | Speed: {speed:.2f} TH/s")
    log(f"Saldo Dompet : {bal:.4f} ODRA | Unclaimed Mined: {mined:.6f} ODRA")
    log(f"Status Wallet: {wallet} | Taps Sisa: {taps_left}")
    log("=" * 50)

    # 1. Collect mined balance
    auto_collect(cfg, state)

    # 2. Daily Checkin
    auto_checkin(cfg, state)

    # 3. Auto-tap
    auto_tap(cfg, state)

    # 4. Auto tasks
    auto_tasks(cfg, state)

    # 5. Claim referral commission
    auto_claim_pool(cfg, state)

    return True

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== ODRA Mining Auto-Farmer Daemon Started ===")
    
    if not cfg.get("init_data"):
        log(">> PERHATIAN: init_data belum diisi di farmers/odra/config.json <<")
        log("Silakan tempelkan initData dari WebApp ODRA untuk memulai auto-farming.")
        if once:
            return

    if once:
        run_cycle(cfg)
        return

    interval = cfg.get("collect_interval_seconds", 600)

    while True:
        try:
            cfg = load_config()
            if cfg.get("init_data"):
                run_cycle(cfg)
            else:
                log("Menunggu init_data di config.json...")
            
            jitter = random.randint(10, 40)
            time.sleep(interval + jitter)
        except KeyboardInterrupt:
            log("Farmer dihentikan oleh pengguna.")
            break
        except Exception as e:
            log(f"Loop unexpected exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
