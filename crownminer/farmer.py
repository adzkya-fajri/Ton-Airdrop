#!/usr/bin/env python3
"""
CrownMiner Telegram Mini-App Auto-Farmer
Handles:
1. Passive mining warehouse collection (/api/game/collect)
2. Daily tap engine auto-flushing (/api/game/tap)
3. Depth milestones auto chest opening (/api/game/chest-open)
4. Real-time resource tracking (Ore, Gold, Shards, Crown, Depth)
"""

import os
import sys
import time
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")

API_BASE = "https://test.crownville.online/cmapi"

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

def get_headers(cfg):
    return {
        "Origin": "https://test.crownville.online",
        "Referer": "https://test.crownville.online/crownminer-stage/game/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
        "Content-Type": "application/json"
    }

def run_farmer():
    log("==================================================")
    log("   CROWNMINER TELEGRAM MINI-APP AUTO-FARMER       ")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            init_data = cfg.get("init_data", "")
            if not init_data:
                log("init_data kosong! Menunggu auto_generator menginjeksi token...")
                time.sleep(30)
                continue

            headers = get_headers(cfg)

            # 1. Fetch current game state
            r = requests.post(f"{API_BASE}/api/game/state", json={"initData": init_data}, headers=headers, timeout=15)
            if r.status_code != 200 or not r.json().get("ok"):
                log(f"Gagal memuat state permainan (HTTP {r.status_code}): {r.text[:200]}")
                time.sleep(60)
                continue

            state = r.json()
            ore = state.get("ore", 0)
            gold = state.get("gold", 0)
            shards = state.get("shards", 0)
            depth = state.get("depth", 0)
            crown = state.get("crown", 0)
            rate_hr = state.get("ratePerHr", 0)
            taps_left = state.get("tapsLeft", 0)

            log(f"⛏️ [STATUS] Kedalaman: {depth:,}m | Rate: {rate_hr}/jam | Shards: {shards} | Emas: {gold} | Bijih: {ore} | Crown: {crown}")

            # 2. Check depth chests
            depth_chests = state.get("depthChests", {})
            ready_chests = depth_chests.get("ready", [])
            for chest_idx in ready_chests:
                try:
                    c_res = requests.post(f"{API_BASE}/api/game/chest-open", json={"initData": init_data, "idx": chest_idx}, headers=headers, timeout=15)
                    log(f"🎁 Buka Peti Kedalaman #{chest_idx}: {c_res.json()}")
                except Exception as ce:
                    log(f"Error buka peti: {ce}")

            # 3. Auto-Tap daily energy
            if taps_left > 0 and not state.get("tapBlocked", False):
                log(f"⚡ Energi Tap Tersedia: {taps_left} tap. Menjalankan auto-tap...")
                while taps_left > 0:
                    batch = min(50, taps_left)
                    t_res = requests.post(f"{API_BASE}/api/game/tap", json={"initData": init_data, "taps": batch}, headers=headers, timeout=15)
                    if t_res.status_code == 200 and t_res.json().get("ok"):
                        res_data = t_res.json()
                        shards = res_data.get("shards", shards)
                        taps_left = res_data.get("tapsLeft", 0)
                        added = res_data.get("added", 0)
                        log(f"⚡ Tap {batch}x Sukses (+{added} shards). Sisa tap: {taps_left} | Total shards: {shards}")
                        if res_data.get("tapBlocked", False):
                            log("Batas harian tap telah tercapai untuk hari ini.")
                            break
                    else:
                        log(f"Auto-tap gagal: {t_res.text[:150]}")
                        break
                    time.sleep(1.5)

            # 4. Collect passive warehouse rewards
            c_res = requests.post(f"{API_BASE}/api/game/collect", json={"initData": init_data}, headers=headers, timeout=15)
            if c_res.status_code == 200 and c_res.json().get("ok"):
                c_data = c_res.json()
                ore = c_data.get("ore", ore)
                gold = c_data.get("gold", gold)
                log(f"📦 [COLLECT] Panen Sukses! Saldo Terkumpul: Bijih = {ore:,} | Emas = {gold:,}")
            else:
                log(f"Collect response: {c_res.text[:150]}")

            # Sleep 15 minutes before next collection cycle
            log("💤 Siklus selesai. Tidur 15 menit sebelum pengumpulan berikutnya...")
            time.sleep(900)

        except Exception as e:
            log(f"Error pada loop utama CrownMiner: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_farmer()
