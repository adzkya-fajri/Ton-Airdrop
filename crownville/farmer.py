#!/usr/bin/env python3
"""
Crownville Telegram Mini-App Auto-Farmer
Mendukung ekosistem Crownville Corp:
1. Auto-Collect Panen Sumber Daya (Emas, Makanan, Bijih, Kayu) via /api/game/collect
2. Auto-Assign Pekerja ke Bangunan Produktif (Market, Farm, dll) via /api/game/assign-workers
3. Auto-Repair Bangunan Rusak via /api/game/repair
4. Auto-Claim Hadiah Quest & Peti Liga
5. Auto Cross-Game Claim Mitra (Crown Miner & Basilisk) via /api/xgame/claim-free
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
API_BASE = "https://crownville.online"

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
    headers = {
        "Origin": "https://crownville.online",
        "Referer": "https://crownville.online/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"),
        "Content-Type": "application/json"
    }
    init_data = cfg.get("init_data", "")
    if init_data:
        headers["X-Telegram-Init-Data"] = init_data
    return headers

def run_farmer():
    log("==================================================")
    log("   CROWNVILLE TELEGRAM MINI-APP AUTO-FARMER       ")
    log("==================================================")

    while True:
        try:
            cfg = load_config()
            init_data = cfg.get("init_data", "")
            if not init_data:
                log("init_data kosong! Menunggu auto_generator menginjeksi token...")
                time.sleep(30)
                continue

            tid = str(cfg.get("telegram_id", "7672016530"))
            uname = cfg.get("username", "Zelx_arthur")
            headers = get_headers(cfg)

            # 1. Fetch current city state
            url_state = f"{API_BASE}/api/game/state?telegram_id={tid}&username={uname}"
            r_state = requests.get(url_state, headers=headers, timeout=15)
            if r_state.status_code != 200:
                log(f"Gagal memuat status kota (HTTP {r_state.status_code}): {r_state.text[:150]}")
                time.sleep(60)
                continue

            state = r_state.json()
            player = state.get("player", {})
            resources = player.get("resources", {})
            gold = round(resources.get("gold", 0), 1)
            food = round(resources.get("food", 0), 1)
            ore = round(resources.get("ore", 0), 1)
            wood = round(resources.get("wood", 0), 1)
            avail_workers = state.get("availableWorkers", 0)
            total_pop = state.get("totalPopulation", 0)
            prod = state.get("productionPerMinute", {})

            log(f"🏰 [KOTA] Warga: {avail_workers}/{total_pop} Luang | Prod/m: Gold +{prod.get('gold',0)}, Food +{prod.get('food',0)}, Ore +{prod.get('ore',0)}, Wood +{prod.get('wood',0)}")
            log(f"💰 [SALDO] Emas: {gold:,} | Makanan: {food:,} | Bijih: {ore:,} | Kayu: {wood:,}")

            # 2. Auto-Collect resources
            if cfg.get("auto_collect", True):
                try:
                    r_coll = requests.post(f"{API_BASE}/api/game/collect", json={"telegram_id": tid}, headers=headers, timeout=15)
                    if r_coll.status_code == 200:
                        c_data = r_coll.json()
                        col = c_data.get("collected", {})
                        if any(v > 0 for v in col.values()):
                            log(f"🌾 [PANEN] Berhasil panen: Emas +{col.get('gold',0)}, Makanan +{col.get('food',0)}, Bijih +{col.get('ore',0)}, Kayu +{col.get('wood',0)}")
                except Exception as ce:
                    log(f"Error saat panen: {ce}")

            # 3. Auto-Assign available workers
            if cfg.get("auto_assign_workers", True) and avail_workers > 0:
                buildings = state.get("buildings", [])
                for b in buildings:
                    b_id = b.get("id")
                    b_type = b.get("type")
                    cur_w = b.get("workers", 0)
                    max_w = b.get("maxWorkers", 0)
                    if max_w > cur_w:
                        assign_cnt = min(avail_workers, max_w - cur_w)
                        try:
                            r_assign = requests.post(f"{API_BASE}/api/game/assign-workers", json={
                                "telegram_id": tid,
                                "building_id": b_id,
                                "workers": cur_w + assign_cnt
                            }, headers=headers, timeout=15)
                            if r_assign.status_code == 200:
                                log(f"👷 [PEKERJA] Berhasil menugaskan +{assign_cnt} pekerja ke {b.get('name', b_type)}!")
                                avail_workers -= assign_cnt
                                if avail_workers <= 0:
                                    break
                        except Exception as we:
                            log(f"Error menugaskan pekerja: {we}")

            # 4. Auto-Repair damaged buildings
            if cfg.get("auto_repair", True):
                buildings = state.get("buildings", [])
                has_damage = any(b.get("currentHp", 0) < b.get("maxHp", 0) for b in buildings)
                if has_damage:
                    try:
                        r_rep = requests.post(f"{API_BASE}/api/game/repair", json={"telegram_id": tid}, headers=headers, timeout=15)
                        if r_rep.status_code == 200:
                            log("🔨 [REPAIR] Bangunan yang rusak telah berhasil diperbaiki!")
                    except Exception as re:
                        log(f"Error perbaikan kota: {re}")

            # 5. Auto Cross-Game Claim (Crown Miner & Basilisk Bonus)
            try:
                r_free = requests.post(f"{API_BASE}/api/xgame/claim-free", json={}, headers=headers, timeout=10)
                if r_free.status_code == 200:
                    f_data = r_free.json()
                    if f_data.get("success") or f_data.get("reward"):
                        log(f"🎁 [CROSS-GAME] Bonus Mitra (Crown Miner / Basilisk) diklaim: {f_data}")
            except Exception:
                pass

            # 6. Auto-Upgrade Buildings (Town Hall, Market, Hut, Hero House)
            if cfg.get("auto_upgrade", True):
                try:
                    now_ts = int(time.time())
                    is_any_upgrading = any(
                        b.get("upgrading") or (b.get("upgradeFinishAt") and b.get("upgradeFinishAt") > now_ts)
                        for b in state.get("buildings", [])
                    )
                    if not is_any_upgrading:
                        buildings = state.get("buildings", [])
                        # Cari level townhall saat ini
                        th_lvl = next((b.get("level", 1) for b in buildings if b.get("type") == "townhall"), 1)

                        # Prioritas upgrade: townhall -> market -> hut -> herohouse
                        priority_order = ["townhall", "market", "hut", "herohouse"]
                        sorted_buildings = sorted(
                            [b for b in buildings if b.get("nextUpgrade")],
                            key=lambda x: priority_order.index(x.get("type")) if x.get("type") in priority_order else 99
                        )

                        for b in sorted_buildings:
                            nxt = b.get("nextUpgrade")
                            if not nxt:
                                continue
                            
                            # Cek dependensi
                            deps_met = True
                            for dep in nxt.get("dependencies", []):
                                dep_type = dep.get("type")
                                min_lvl = dep.get("minLevel", 1)
                                curr_dep_lvl = next((x.get("level", 1) for x in buildings if x.get("type") == dep_type), 0)
                                if curr_dep_lvl < min_lvl:
                                    deps_met = False
                                    break
                            
                            if not deps_met:
                                continue

                            # Cek freeResources
                            free_req = nxt.get("freeResources") or nxt.get("resources") or {}
                            can_afford = (
                                gold >= free_req.get("gold", 0) and
                                food >= free_req.get("food", 0) and
                                wood >= free_req.get("wood", 0) and
                                ore >= free_req.get("ore", 0)
                            )

                            if can_afford:
                                b_id = b.get("id")
                                target_lvl = nxt.get("targetLevel", b.get("level", 1) + 1)
                                b_name = b.get("name", b.get("type"))
                                log(f"🏗️ [UPGRADE] Memulai upgrade {b_name} ke Level {target_lvl} (Mode Free)...")
                                r_up = requests.post(
                                    f"{API_BASE}/api/game/upgrade",
                                    json={"telegram_id": tid, "building_id": b_id, "freeMode": True},
                                    headers=headers,
                                    timeout=15
                                )
                                if r_up.status_code == 200:
                                    up_data = r_up.json()
                                    log(f"✅ [UPGRADE] Sukses memulai upgrade {b_name} Lv {target_lvl}!")
                                    break
                                else:
                                    log(f"⚠️ [UPGRADE] Gagal upgrade {b_name}: {r_up.text[:100]}")
                    else:
                        for b in state.get("buildings", []):
                            if b.get("upgrading") or (b.get("upgradeFinishAt") and b.get("upgradeFinishAt") > now_ts):
                                rem = max(0, (b.get("upgradeFinishAt") or 0) - now_ts)
                                log(f"⏳ [UPGRADE] {b.get('name', b.get('type'))} sedang proses naik level (Sisa: {rem//60}m {rem%60}s)")
                except Exception as ue:
                    log(f"Error pada proses auto-upgrade: {ue}")

            # 7. Check & Claim Quests
            if cfg.get("auto_quests", True):
                try:
                    r_q = requests.get(f"{API_BASE}/api/game/quests", headers=headers, timeout=10)
                    if r_q.status_code == 200:
                        q_data = r_q.json()
                        quests = q_data.get("quests", [])
                        for q in quests:
                            if q.get("current", 0) >= q.get("target", 1) and not q.get("claimed", False):
                                q_id = q.get("id")
                                r_qc = requests.post(f"{API_BASE}/api/game/quests/{q_id}/claim", json={"telegram_id": tid}, headers=headers, timeout=10)
                                if r_qc.status_code == 200:
                                    log(f"🏆 [QUEST] Quest selesai diklaim: '{q.get('title')}'!")
                except Exception as qe:
                    log(f"Error klaim quest: {qe}")

            # Interval sleep
            interval = cfg.get("check_interval_seconds", 600)
            log(f"💤 Siklus selesai. Tidur {interval // 60} menit sebelum siklus panen berikutnya...")
            time.sleep(interval)

        except Exception as e:
            log(f"Error pada loop utama Crownville: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_farmer()
