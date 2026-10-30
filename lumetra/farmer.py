#!/usr/bin/env python3
"""
LumeTRA Telegram Mini-App Auto-Farmer ($LMTR)
Automates:
1. Auto-login and JWT token exchange with init_data
2. 24-Hour Mining Cycle Auto-Claim & Auto-Start
3. Daily Tasks & Check-in Auto-Claim
4. Real-time balance, level, and hashrate speed tracking
"""

import os
import sys
import time
import json
import requests
import urllib.parse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")

API_BASE = "https://api.lumetramine.com/api"

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
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def login(cfg):
    init_data = cfg.get("init_data", "")
    if not init_data:
        log("init_data kosong! Menunggu disuntik oleh auth_generator...")
        return None

    try:
        qs = urllib.parse.parse_qs(init_data)
        u_obj = json.loads(qs.get("user", ["{}"])[0])
        payload = {
            "tg_id": u_obj.get("id"),
            "name": u_obj.get("first_name", "Local Miner"),
            "photo_url": u_obj.get("photo_url", ""),
            "startapp": cfg.get("startapp", "ref_8324041139"),
            "init_data": init_data
        }
        headers = {
            "Origin": "https://web.lumetramine.com",
            "Referer": "https://web.lumetramine.com/",
            "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
            "Content-Type": "application/json"
        }
        r = requests.post(f"{API_BASE}/login", json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            res_json = r.json()
            if res_json.get("code") == 1:
                token = res_json.get("data", {}).get("token")
                if token:
                    cfg["token"] = token
                    save_config(cfg)
                    log(f"Login sukses LumeTRA! User: {u_obj.get('first_name')} (ID: {u_obj.get('id')})")
                    return token
        log(f"Login gagal: HTTP {r.status_code} - {r.text[:200]}")
    except Exception as e:
        log(f"Exception saat login LumeTRA: {e}")
    return None

def get_headers(cfg, token):
    return {
        "Origin": "https://web.lumetramine.com",
        "Referer": "https://web.lumetramine.com/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

def process_tasks(headers, tasks_list):
    for t in tasks_list:
        tid = t.get("id")
        title = t.get("title", tid)
        completed = t.get("completed", False)
        # Skip tasks that require holding coins or deposits
        if t.get("type") == "holding":
            continue
        if not completed:
            try:
                # Open first if required
                if not t.get("opened", False):
                    requests.post(f"{API_BASE}/tasks/open", json={"task_id": tid}, headers=headers, timeout=10)
                    time.sleep(1.5)
                c_res = requests.post(f"{API_BASE}/tasks/claim", json={"task_id": tid}, headers=headers, timeout=10)
                if c_res.status_code == 200 and c_res.json().get("code") == 1:
                    rew = t.get("reward", 0)
                    log(f"🎁 >> BERHASIL KLAIM TASK '{title}'! (+{rew} LMTR) <<")
            except Exception as e:
                log(f"Task {tid} error: {e}")

def run_farmer():
    log("==================================================")
    log("   LUMETRA ($LMTR) TELEGRAM MINI-APP AUTO-FARM    ")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            token = cfg.get("token", "")
            if not token:
                token = login(cfg)
                if not token:
                    time.sleep(30)
                    continue

            headers = get_headers(cfg, token)

            # 1. Fetch Bootstrap
            r = requests.get(f"{API_BASE}/bootstrap", headers=headers, timeout=15)
            if r.status_code in (401, 403) or (r.status_code == 200 and r.json().get("code") in (2, 401)):
                log("Token expired atau tidak valid, me-refresh login...")
                token = login(cfg)
                if not token:
                    time.sleep(30)
                    continue
                headers = get_headers(cfg, token)
                r = requests.get(f"{API_BASE}/bootstrap", headers=headers, timeout=15)

            if r.status_code != 200:
                log(f"Gagal bootstrap LumeTRA: HTTP {r.status_code}")
                time.sleep(60)
                continue

            boot_data = r.json().get("data", {})
            user_data = boot_data.get("user", {})
            pool_balance = float(user_data.get("pool_balance", 0.0))
            level = user_data.get("level", 1)
            speed = float(user_data.get("speed", 0.2))
            mining = user_data.get("mining", {})
            is_active = mining.get("active", False)
            pending = float(mining.get("pending", 0.0))
            ends_at = mining.get("ends_at")
            tasks = boot_data.get("tasks", [])

            log(f"⛏️ [STATUS] Saldo Pool: {pool_balance:.4f} LMTR | Level {level} (Speed: {speed:.4f}/jam)")

            # Process eligible tasks
            process_tasks(headers, tasks)

            now = int(time.time())

            # Check if claim is needed
            if not is_active or (ends_at and now >= ends_at) or pending > 0:
                if pending > 0 or (ends_at and now >= ends_at):
                    log(f"🌾 Sesi mining selesai / pending reward tersedia ({pending:.4f} LMTR). Mengklaim...")
                    c_res = requests.post(f"{API_BASE}/mining/claim", json={}, headers=headers, timeout=15)
                    if c_res.status_code == 200 and c_res.json().get("code") == 1:
                        c_user = c_res.json().get("data", {})
                        pool_balance = float(c_user.get("pool_balance", pool_balance))
                        log(f"🎉 >> KLAIM BERHASIL! << Saldo Pool Baru: {pool_balance:.4f} LMTR | Level: {c_user.get('level')}")

                # Start new 24h cycle
                log("🚀 Menyalakan mesin mining LumeTRA...")
                s_res = requests.post(f"{API_BASE}/mining/start", json={}, headers=headers, timeout=15)
                if s_res.status_code == 200 and s_res.json().get("code") == 1:
                    s_data = s_res.json().get("data", {})
                    ends_at = s_data.get("mining", {}).get("ends_at", now + 86400)
                    finish_str = datetime.fromtimestamp(ends_at).strftime("%d/%m/%Y %H:%M:%S")
                    log(f"🟢 Mining Aktif (24 Jam)! Selesai pada: {finish_str}")
                else:
                    ends_at = now + 86400
            else:
                rem = max(0, ends_at - now)
                hours = rem // 3600
                mins = (rem % 3600) // 60
                finish_str = datetime.fromtimestamp(ends_at).strftime("%d/%m/%Y %H:%M:%S")
                log(f"⏳ Mining Sedang Berjalan: Sisa {hours}j {mins}m (Selesai pada: {finish_str})")

            # Heartbeat check every 15 minutes
            log("💤 Menunggu 15 menit untuk siklus pemeriksaan berikutnya...")
            time.sleep(900)

        except Exception as e:
            log(f"Error pada loop utama LumeTRA: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_farmer()
