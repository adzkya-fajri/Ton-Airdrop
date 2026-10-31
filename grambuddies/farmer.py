#!/usr/bin/env python3
"""
Gram Buddies Auto-Farmer Daemon
- Auto-claim Daily Login
- Auto-spin Lucky Wheel (Semua putaran harian)
- Auto-claim Tasks (Kategori: official, sponsored, earn, premium)
  * Mematuhi safety rule: tidak mengklaim task dengan instruksi 'hold' atau deposit
- Auto-Mining dengan 100% Seluruh Poin / Power yang dimiliki
- Auto-Collect hasil tambang saat sesi mining selesai
"""

import json
import os
import sys
import time
import random
import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "farmer.log")
BASE_URL = "https://buddies.name.ng/api"

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
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://buddies.name.ng",
        "Referer": "https://buddies.name.ng/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36"),
        "X-Device-Id": cfg.get("device_id", ""),
        "X-Telegram-Init-Data": cfg.get("init_data", "")
    }

def api_request(cfg, endpoint, method="GET", json_data=None):
    url = f"{BASE_URL}/{endpoint}"
    headers = get_headers(cfg)
    try:
        if method == "POST":
            res = requests.post(url, headers=headers, json=json_data, timeout=20)
        else:
            res = requests.get(url, headers=headers, timeout=20)

        if res.status_code in [200, 400]:
            try:
                return res.json()
            except Exception:
                return {"ok": False, "error": res.text}
        elif res.status_code == 401:
            log(f"⚠️ [Auth] Sesi otentikasi tidak valid atau kadaluarsa (HTTP 401): {res.text}")
            return {"ok": False, "error": "auth_failed"}
        else:
            log(f"⚠️ [HTTP {res.status_code}] {endpoint}: {res.text[:100]}")
            return {"ok": False, "error": f"http_{res.status_code}"}
    except Exception as e:
        log(f"⚠️ [Network] Error akses {endpoint}: {e}")
        return {"ok": False, "error": str(e)}

def do_daily_login(cfg):
    data = api_request(cfg, "daily_login.php", method="POST")
    if data and data.get("ok"):
        if data.get("already_today"):
            pass
        elif data.get("login_reward"):
            rew = data["login_reward"]
            pts = rew.get("points", 0)
            gems = rew.get("gems", 0)
            log(f"🎁 [Daily Login] Klaim Hari Ke-{data.get('user', {}).get('login_streak', 1)}: +{pts} Pts, +{gems} GEMS!")
            return data.get("user")
    return None

def do_spins(cfg):
    total_won_pts = 0
    total_won_gems = 0.0
    spins_done = 0

    while True:
        data = api_request(cfg, "spin.php", method="POST", json_data={"spin": 1})
        if not data or not data.get("ok"):
            break

        spins_done += 1
        label = data.get("prize_label", "Prize")
        ptype = data.get("prize_type", "")
        pval = data.get("prize_value", 0)

        if ptype == "points":
            total_won_pts += pval
        elif ptype == "gems":
            total_won_gems += float(pval)

        log(f"🎡 [Lucky Spin] Putaran {spins_done}: Menang '{label}' (Sisa: {data.get('spins_left', 0)})")

        if data.get("spins_left", 0) <= 0:
            break
        time.sleep(1.5)

    if spins_done > 0:
        if total_won_gems > 0:
            log(f"Klaim Sukses      : +{total_won_gems:.2f} GEMS (Lucky Wheel)")
        log(f"🎡 [Lucky Spin] Selesai ({spins_done} putaran): Total +{total_won_pts} Pts, +{total_won_gems:.2f} GEMS.")

def do_tasks(cfg):
    categories = ["official", "sponsored", "earn", "premium"]
    total_claimed_pts = 0
    total_claimed_gems = 0.0

    for cat in categories:
        data = api_request(cfg, f"tasks_list.php?category={cat}")
        if not data or not data.get("ok"):
            continue

        tasks = data.get("tasks", [])
        for t in tasks:
            tid = t.get("id")
            title = t.get("title", "")
            status = t.get("status", "")
            verify_type = t.get("verify_type", "")
            desc = t.get("description", "").lower()
            t_title_lower = title.lower()

            # Safety Rule: Abaikan task dengan ketentuan 'hold' atau deposit
            if "hold" in desc or "hold" in t_title_lower or "deposit" in desc or "deposit" in t_title_lower:
                continue

            # Hanya klaim task yang statusnya 'available'
            if status == "available":
                # verifikasi otomatis: none & channel_membership
                if verify_type in ["none", "channel_membership"]:
                    res = api_request(cfg, "task_claim.php", method="POST", json_data={"task_id": tid})
                    if res and res.get("ok") and res.get("status") == "approved":
                        r_pts = res.get("reward_points", 0)
                        r_gems = float(res.get("reward_gems", 0))
                        total_claimed_pts += r_pts
                        total_claimed_gems += r_gems
                        log(f"📋 [Task] Berhasil Klaim '{title}': +{r_pts} Pts, +{r_gems:.2f} GEMS")
                    elif res and res.get("error") == "not_member":
                        # Belum join channel terkait
                        pass
                    time.sleep(1.0)

    if total_claimed_pts > 0 or total_claimed_gems > 0:
        log(f"📋 [Task Summary] Hari ini diklaim: +{total_claimed_pts} Pts, +{total_claimed_gems:.2f} GEMS")

def do_missions(cfg):
    """Mengklaim misi pencapaian (watch ads, referral, dll)"""
    data = api_request(cfg, "missions.php")
    if not data or not data.get("ok"):
        return

    missions = data.get("missions", [])
    for m in missions:
        mid = m.get("id")
        title = m.get("title", "")
        claimed = m.get("claimed", False)
        can_claim = m.get("can_claim", False)

        if can_claim and not claimed:
            res = api_request(cfg, "mission_claim.php", method="POST", json_data={"mission_id": mid})
            if res and res.get("ok"):
                r_pts = res.get("reward_points", 0)
                r_gems = float(res.get("reward_gems", 0))
                log(f"🎯 [Mission] Berhasil Klaim Misi '{title}': +{r_pts} Pts, +{r_gems:.2f} GEMS!")
                if r_gems > 0:
                    log(f"Klaim Sukses      : +{r_gems:.2f} GEMS")
            time.sleep(1.0)

def do_ad_tasks(cfg, max_monetag=5, max_bitvex=5, max_gigapub=5, max_adsgram=5):
    """
    Menonton tugas iklan otomatis (semua provider iklan):
    - Monetag: hingga 300 iklan/hari (+10 Pts/iklan)
    - AdsBitvex: hingga 200 iklan/hari (+20 Pts/iklan)
    - Gigapub: hingga 500 iklan/hari (+25 Pts/iklan)
    - Adsgram: video ads standar (+10 Pts/iklan)
    Dijalankan secara berkala bertahap setiap siklus dengan jeda natural.
    """
    total_pts = 0
    ads_done = 0

    # 1. Monetag Ads (+10 Pts)
    for _ in range(max_monetag):
        res = api_request(cfg, "earn_points_ad.php", method="POST", json_data={"provider": "monetag"})
        if not res or not res.get("ok"):
            break
        watched = res.get("ads_watched_today", 0)
        limit = res.get("ad_daily_limit", 300)
        rew = res.get("reward_points", 10)
        total_pts += rew
        ads_done += 1
        if watched >= limit:
            break
        time.sleep(random.uniform(4.0, 7.0))

    # 2. AdsBitvex Ads (+20 Pts)
    for _ in range(max_bitvex):
        res = api_request(cfg, "adsbitvex_reward.php", method="POST", json_data={})
        if not res or not res.get("ok"):
            break
        watched = res.get("watched_today", 0)
        limit = res.get("daily_limit", 200)
        rew = res.get("reward_points", 20)
        total_pts += rew
        ads_done += 1
        if watched >= limit:
            break
        time.sleep(random.uniform(4.0, 7.0))

    # 3. Gigapub Ads (+25 Pts)
    for _ in range(max_gigapub):
        res = api_request(cfg, "gigapub_reward.php", method="POST", json_data={})
        if not res or not res.get("ok"):
            break
        watched = res.get("watched_today", 0)
        limit = res.get("daily_limit", 500)
        rew = res.get("reward_points", 25)
        total_pts += rew
        ads_done += 1
        if watched >= limit:
            break
        time.sleep(random.uniform(4.0, 7.0))

    # 4. Adsgram Ads (+10 Pts)
    for _ in range(max_adsgram):
        res = api_request(cfg, "adsgram_reward.php", method="POST", json_data={})
        if not res or not res.get("ok"):
            break
        watched = res.get("ads_watched_today", 0)
        limit = res.get("ad_daily_limit", 300)
        rew = res.get("reward_points", 10)
        total_pts += rew
        ads_done += 1
        if watched >= limit:
            break
        time.sleep(random.uniform(4.0, 7.0))

    if ads_done > 0:
        log(f"📺 [Ad Tasks] Batch {ads_done} iklan selesai: +{total_pts} Pts terkumpul!")
        do_missions(cfg)

def do_mining_cycle(cfg):
    """
    Mengelola siklus penambangan:
    1. Periksa sesi penambangan aktif
    2. Jika siap klaim (ready_at tercapai): klaim reward gems
    3. Jika tidak ada sesi aktif: pasang SELURUH poin/power yang dimiliki ke miner
    """
    me_data = api_request(cfg, "me.php")
    if not me_data or not me_data.get("ok"):
        log("⚠️ Gagal memuat data profil me.php")
        return 600

    user = me_data.get("user", {})
    mining = me_data.get("mining")
    miner_configs = me_data.get("miner_configs", [])
    tier = user.get("miner_tier", "free")

    tier_cfg = next((c for c in miner_configs if c.get("tier") == tier), None)
    max_pts_allowed = tier_cfg.get("points_max", 10000) if tier_cfg else 10000

    # 1. Cek sesi mining yang berjalan
    if mining:
        is_ready = mining.get("is_ready", False)
        sec_left = mining.get("seconds_left", 0)

        if is_ready or sec_left <= 0:
            log(f"⛏️ Sesi mining #{mining.get('id')} selesai! Mengumpulkan GEMS...")
            col_res = api_request(cfg, "mining_collect.php", method="POST")
            if col_res and col_res.get("ok"):
                earned_gems = float(mining.get("gems_to_earn", 0))
                log(f"Klaim Sukses      : +{earned_gems:.2f} GEMS")
                log(f"💎 [Mining Collect] Sukses mengklaim +{earned_gems:.2f} GEMS! Saldo diperbarui.")
                # Refresh data profil
                me_data = api_request(cfg, "me.php")
                if me_data and me_data.get("ok"):
                    user = me_data.get("user", {})
                    mining = None
            else:
                log(f"⚠️ Gagal collect mining: {col_res}")

    # 2. Jika tidak ada sesi aktif (atau baru saja di-collect): Mulai sesi baru dengan SELURUH POIN
    if not mining:
        pts = user.get("points", 0)
        pts_to_load = min(pts, max_pts_allowed)

        if pts_to_load >= 1:
            log(f"⚡ [Mining Load] Memulai sesi tambang dengan SELURUH POWER ({pts_to_load} Points) pada Miner Tier '{tier.upper()}'...")
            load_res = api_request(cfg, "mining_load.php", method="POST", json_data={"points": pts_to_load, "booster_id": 0})
            if load_res and load_res.get("ok"):
                new_mining = load_res.get("mining", {})
                gems_est = new_mining.get("gems_to_earn", 0)
                dur_h = new_mining.get("duration_seconds", 43200) / 3600
                log(f"⛏️ [Mining Aktif] Berhasil! Beban: {pts_to_load} Pts | Estimasi: +{gems_est} GEMS | Durasi: {dur_h:.1f} jam.")
                mining = new_mining
            else:
                log(f"⚠️ Gagal load mining: {load_res}")
        else:
            log(f"ℹ️ [Mining Standby] Saldo poin saat ini: {pts} Pts. Menunggu perolehan poin dari task/daily.")

    # 3. Log Status Saldo & Ringkasan untuk Dashboard
    gems_bal = float(user.get("gems", 0.0))
    pts_bal = user.get("points", 0)
    log(f"Total Saldo Gems  : {gems_bal:.2f}")
    log(f"Total Saldo Points: {pts_bal}")
    log(f"Total Saldo       : {gems_bal:.2f} GEMS ({pts_bal} Pts)")

    if mining and not mining.get("is_ready"):
        sec_left = max(0, mining.get("seconds_left", 0))
        h_left = sec_left // 3600
        m_left = (sec_left % 3600) // 60
        ready_at = mining.get("ready_at", "")
        # Format WIB
        try:
            dt_utc = datetime.datetime.fromisoformat(ready_at.replace("Z", "+00:00"))
            dt_wib = dt_utc + datetime.timedelta(hours=7)
            ready_str = dt_wib.strftime("%H:%M:%S")
        except Exception:
            ready_str = ready_at

        log(f"Mining Status     : Running ({mining.get('points_loaded')} pts loaded)")
        log(f"Next Klaim        : {ready_str} WIB ({h_left}j {m_left}m tersisa)")
        # Hitung jeda tidur: kembali memeriksa setiap 10-15 menit atau ketika mining selesai
        sleep_dur = min(900, sec_left + 10)
        return max(60, sleep_dur)
    else:
        log(f"Mining Status     : Standby / Ready")
        log(f"Next Klaim        : Segera saat poin tersedia")
        return 600

def run_loop():
    log("==================================================")
    log("🚀 GRAM BUDDIES AUTO-FARMER DAEMON DIMULAI")
    log("⚡ Mode: Auto Tasks + Max Power Mining (100% Poin)")
    log("==================================================")

    last_task_check = 0
    last_daily_check = 0

    while True:
        try:
            cfg = load_config()
            now = time.time()

            # 1. Daily Login (periksa setiap 4 jam atau pergantian hari)
            if now - last_daily_check > 14400:
                do_daily_login(cfg)
                last_daily_check = now

            # 2. Spin Wheel (periksa setiap siklus jika ada putaran tersisa)
            do_spins(cfg)

            # 3. Auto Tasks (periksa setiap 30 menit)
            if now - last_task_check > 1800:
                do_tasks(cfg)
                do_missions(cfg)
                last_task_check = now

            # 4. Ad Tasks (Monetag, AdsBitvex, Gigapub, Adsgram bertahap setiap siklus)
            do_ad_tasks(cfg, max_monetag=5, max_bitvex=5, max_gigapub=5, max_adsgram=5)

            # 5. Mining Management (Collect & Load Max Power)
            next_sleep = do_mining_cycle(cfg)

            # Tambah random jitter 5-15 detik
            sleep_time = next_sleep + random.randint(5, 15)
            log(f"💤 Tidur selama {sleep_time // 60} menit {sleep_time % 60} detik...")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            log("🛑 Gram Buddies Farmer dihentikan oleh pengguna.")
            break
        except Exception as e:
            log(f"⚠️ Error loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_loop()
