#!/usr/bin/env python3
"""
VYQ Miner (@VYQMiners_bot) Auto-Farmer Daemon
DEX Pair: STON.fi ($VYQ / $GRAM)
Automasi:
1. Auto-login & bearer token exchange dari tgWebAppData
2. Auto-start mining jika status mining tidak aktif
3. Auto-claim mined VYQ balance via /api/mining/claim
4. Auto-claim referral rewards via /api/referrals/claim
5. Auto-complete & claim non-risk social tasks
6. Tracking metric saldo VYQ & kecepatan mining (speed/h)
7. Dynamic config reload & adaptive backoff
"""

import os
import sys
import time
import json
import urllib.parse
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
API_BASE = "https://api.vyqminer.top/api"

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
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error membaca config: {e}")
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log(f"Gagal menyimpan config: {e}")

def get_headers(token=None, cfg=None):
    if cfg is None:
        cfg = {}
    h = {
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Referer": "https://web.vyqminer.top/",
        "Origin": "https://web.vyqminer.top",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*"
    }
    if token:
        clean_token = token.replace("Bearer ", "").strip()
        h["Authorization"] = f"Bearer {clean_token}"
    return h

def login_exchange(cfg):
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
        headers = get_headers(cfg=cfg)
        r = requests.post(f"{API_BASE}/login", json=payload, headers=headers, timeout=15)
        if r.status_code == 200 and r.json().get("code") == 1:
            token = r.json().get("data", {}).get("token", "")
            if token:
                cfg["token"] = token
                save_config(cfg)
                log(">> Berhasil login & menukar init_data menjadi Bearer token VYQ <<")
                return token
        else:
            log(f"[VYQ] Login gagal (HTTP {r.status_code}): {r.text[:100]}")
    except Exception as e:
        log(f"[VYQ] Exception login exchange: {e}")
    return None

def fetch_bootstrap(token, cfg):
    headers = get_headers(token, cfg)
    try:
        r = requests.get(f"{API_BASE}/bootstrap", headers=headers, timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res.get("code") == 1:
                return res.get("data", {})
        elif r.status_code in (401, 403):
            log(f">> Token VYQ Expired (HTTP {r.status_code})! Perlu Update Token / Re-login <<")
            return "EXPIRED"
        else:
            log(f"[VYQ] Bootstrap HTTP {r.status_code}: {r.text[:80]}")
    except Exception as e:
        log(f"[VYQ] Exception bootstrap: {e}")
    return None

def check_and_claim_mining(token, user_data, cfg):
    mining = user_data.get("mining") or {}
    active = mining.get("active", False)
    pending = float(mining.get("pending", 0) or 0)
    ends_at = int(mining.get("ends_at", 0) or 0)
    now_ts = int(time.time())

    headers = get_headers(token, cfg)

    # 1. Start mining if inactive or expired
    if not active or (ends_at > 0 and now_ts >= ends_at):
        log("[VYQ] Sesi mining tidak aktif / telah berakhir. Mengirim request /api/mining/start...")
        try:
            r_start = requests.post(f"{API_BASE}/mining/start", headers=headers, json={}, timeout=15)
            if r_start.status_code == 200 and r_start.json().get("code") == 1:
                log(">> Berhasil memulai siklus mining VYQ baru! <<")
            else:
                log(f"[VYQ] Gagal start mining: {r_start.text[:80]}")
        except Exception as e:
            log(f"[VYQ] Exception start mining: {e}")

    # 2. Claim pending mining reward jika mencapai batas minimal (>= 0.1 VYQ) atau jika mining berhenti
    if pending >= 0.1 or (not active and pending > 0):
        log(f"[VYQ] Terdeteksi pending reward: {pending:.4f} VYQ. Mengirim request /api/mining/claim...")
        try:
            r_claim = requests.post(f"{API_BASE}/mining/claim", headers=headers, json={}, timeout=15)
            if r_claim.status_code == 200 and r_claim.json().get("code") == 1:
                claimed_user = r_claim.json().get("data", {})
                new_assets = float(claimed_user.get("assets", 0) or 0)
                log("=" * 50)
                log(f">> KLAIM MINING VYQ BERHASIL! +{pending:.4f} VYQ <<")
                log(f"Saldo Total Sekarang: {new_assets:,.4f} VYQ")
                log("=" * 50)
                return True
            else:
                log(f"[VYQ] Gagal claim mining: {r_claim.text[:80]}")
        except Exception as e:
            log(f"[VYQ] Exception claim mining: {e}")

    return False

def check_and_claim_referrals(token, user_data, cfg):
    ref_avail = float(user_data.get("referral_available", 0) or 0)
    if ref_avail > 0:
        log(f"[VYQ] Terdeteksi referral reward: {ref_avail:.4f} VYQ. Mengklaim...")
        headers = get_headers(token, cfg)
        try:
            r = requests.post(f"{API_BASE}/referrals/claim", headers=headers, json={}, timeout=15)
            if r.status_code == 200 and r.json().get("code") == 1:
                log(f">> Berhasil klaim komisi referral: +{ref_avail:.4f} VYQ! <<")
        except Exception as e:
            log(f"[VYQ] Exception claim referral: {e}")

def process_tasks(token, tasks, cfg):
    headers = get_headers(token, cfg)
    for t in tasks:
        tid = t.get("id")
        title = t.get("title", "")
        completed = t.get("completed", False)
        validation = t.get("validation", "")

        # Hanya selesaikan task non-risiko sosial/kunjungan yang belum selesai
        if not completed and validation in ("visit", "instant"):
            opened = t.get("opened", False)
            if not opened and t.get("url"):
                try:
                    requests.post(f"{API_BASE}/tasks/open", headers=headers, json={"task_id": tid}, timeout=10)
                    time.sleep(1)
                except Exception:
                    pass
            try:
                r_c = requests.post(f"{API_BASE}/tasks/claim", headers=headers, json={"task_id": tid}, timeout=12)
                if r_c.status_code == 200 and r_c.json().get("code") == 1:
                    rew = t.get("reward", 0)
                    log(f">> Berhasil klaim task '{title}': +{rew} VYQ! <<")
                    time.sleep(1.5)
            except Exception as e:
                log(f"[VYQ] Error claiming task {tid}: {e}")

def run_loop():
    log("=== VYQ Miner Auto-Farmer Daemon Dimulai ===")
    
    while True:
        try:
            cfg = load_config()
            token = cfg.get("token", "").strip()

            if not token:
                # Coba login dari init_data jika token belum ada
                token = login_exchange(cfg)

            if not token:
                log("Token/initData VYQ kosong di config.json. Menunggu auth generator...")
                time.sleep(15)
                continue

            boot = fetch_bootstrap(token, cfg)
            if boot == "EXPIRED":
                # Coba login ulang via init_data
                token = login_exchange(cfg)
                if not token:
                    time.sleep(20)
                    continue
                boot = fetch_bootstrap(token, cfg)

            if not boot or not isinstance(boot, dict):
                time.sleep(20)
                continue

            user_data = boot.get("user", {})
            name = user_data.get("name", "Zalx")
            assets = float(user_data.get("assets", 0) or 0)
            speed = float(user_data.get("speed", 0.2) or 0.2)
            mining = user_data.get("mining") or {}
            m_active = mining.get("active", False)
            pending = float(mining.get("pending", 0) or 0)

            # 1. Start & Claim mining
            check_and_claim_mining(token, user_data, cfg)

            # 2. Check and claim referral bonuses
            check_and_claim_referrals(token, user_data, cfg)

            # 3. Process social tasks
            tasks = boot.get("tasks", [])
            if tasks:
                process_tasks(token, tasks, cfg)

            log(f"[VYQ] Status: Normal | Akun: {name} | Saldo: {assets:,.4f} VYQ | Speed: {speed}/h | Pending: {pending:.4f} VYQ | Mining: {'Aktif' if m_active else 'Mati'}")

        except Exception as e:
            log(f"[VYQ] Loop Error: {e}")

        # Sleep interval (60 detik)
        time.sleep(60)

if __name__ == "__main__":
    run_loop()
