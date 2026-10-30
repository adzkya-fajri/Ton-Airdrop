#!/usr/bin/env python3
"""
Monsterland Telegram Mini-App Auto-Farmer & Pet Care Daemon
Mini-App: @monsterland_bot (https://lets.playmonsterland.com/)
Fitur Otomasi Perawatan Pet:
- 🍎 Memberi Makan (Feed pet with Magic Apple / Inventory food until target threshold)
- 🧼 Membersihkan Badan (Bath / Clean pet with Magic Towel until target threshold)
- ☕ Memberi Kopi (Give Wizard Coffee for instant +20 Energy boost until target threshold)
- 🛒 Membeli Keperluan (Auto-purchase care consumables with $LUMIS balance)
- ⚡ Sleep & Wake Management (Wake up pet when energised to maximize $LUMIS mining)
- 🎁 Daily Streak Auto-Claim
- 🔄 Adaptive Sleep & Hot-Reload config.json
"""

import os
import sys
import time
import json
import random
import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "farmer.log")
BASE_URL = "https://lets.playmonsterland.com"

# Item Care Mappings (ID, Name, Emoji, Vital, Restore Value, Base Lumis Price)
# Sesuai definisi resmi game bundle Next.js (module 170026):
CARE_ITEMS = {
    "food": {
        "magic_apple": {"name": "Magic Apple", "emoji": "🍎", "vital": "food", "value": 15, "base_price": 250},
        "hunger_potion": {"name": "Hunger Potion (Tier 5)", "emoji": "🧪", "vital": "food", "value": 50, "base_price": 28000}
    },
    "hygiene": {
        "fairy_bath": {"name": "Fairy Bath", "emoji": "🛁", "vital": "hygiene", "value": 20, "base_price": 200}
    },
    "energy": {
        "wizard_coffee": {"name": "Wizard Coffee", "emoji": "☕", "vital": "energy", "value": 20, "base_price": 300}
    }
}

def get_store_price(item_id, profile=None):
    """Menghitung harga riil item di toko berdasarkan skala konversi ekonomi game (scaleLumis)."""
    base_prices = {"magic_apple": 250, "fairy_bath": 200, "wizard_coffee": 300, "hunger_potion": 28000}
    base = base_prices.get(item_id, 250)
    lumis_per_usd = 10000000
    if profile and isinstance(profile, dict):
        lumis_per_usd = profile.get("lumis_per_usd", 10000000)
    scale = max(1.0, lumis_per_usd / 1000000.0)
    return int(base * scale)

def select_best_vital_item(vital_type, deficit, inventory, lumis_balance, min_reserve, profile=None):
    """
    Memilih item vitals paling optimal:
    1. Utamakan barang gratis/iklan yang sudah ada di inventory (action: 'use_inventory').
    2. Jika inventory kosong, periksa apakah saldo LUMIS cukup untuk membeli via Toko Game ('buy_and_use').
    3. Jika defisit besar (>= 60%), pilih item tier tinggi jika terjangkau.
    4. Jika saldo belum cukup, kembalikan None agar menunggu akumulasi hasil tambang.
    """
    items_dict = CARE_ITEMS.get(vital_type, {})
    sorted_by_val = sorted(items_dict.items(), key=lambda x: x[1]["value"], reverse=True)

    # 1. Cek inventory terlebih dahulu (gratis / hasil iklan / drop)
    for i_id, info in sorted_by_val:
        if inventory.get(i_id, 0) > 0:
            return i_id, info, "use_inventory"

    # 2. Pembelian via Toko Game: sesuaikan dengan harga skala riil
    affordable_items = []
    for i_id, info in sorted_by_val:
        cost = get_store_price(i_id, profile)
        if lumis_balance >= (cost + min_reserve):
            affordable_items.append((i_id, {**info, "price": cost}))

    if not affordable_items:
        return None, None, None

    # Jika keperluan tinggi (deficit >= 60), pilih tier tinggi
    if deficit >= 60:
        for i_id, info in affordable_items:
            if info["value"] >= 50:
                return i_id, info, "buy_and_use"
    elif deficit >= 30:
        for i_id, info in affordable_items:
            if 30 <= info["value"] <= 60:
                return i_id, info, "buy_and_use"

    # Fallback ke item termurah yang terjangkau
    cheapest = min(affordable_items, key=lambda x: x[1]["price"])
    return cheapest[0], cheapest[1], "buy_and_use"

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
    auth = cfg.get("authorization", "").strip()
    if not auth.startswith("tma ") and auth.startswith("user="):
        auth = f"tma {auth}"
        
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://lets.playmonsterland.com",
        "Referer": "https://lets.playmonsterland.com/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.107 Mobile Safari/537.36"),
        "Authorization": auth
    }
    turnstile = cfg.get("cf_turnstile_token", "").strip()
    if turnstile:
        headers["cf-turnstile-response"] = turnstile
    return headers

def fetch_user_data(cfg):
    url = f"{BASE_URL}/api/user?include=monsters"
    try:
        r = requests.get(url, headers=get_headers(cfg), timeout=15)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 401:
            log(">> ERROR 401: Authorization / initData Monsterland kadaluarsa! <<")
            return "UNAUTHORIZED"
        elif r.status_code == 403:
            data = r.json() if r.text else {}
            if data.get("error") == "TURNSTILE_REQUIRED":
                log(">> PERINGATAN: Cloudflare Turnstile diperlukan oleh server Monsterland! <<")
                return "TURNSTILE_REQUIRED"
            log(f"Akses ditolak (HTTP 403): {r.text[:120]}")
            return None
        else:
            log(f"Gagal mengambil info user (HTTP {r.status_code}): {r.text[:150]}")
    except Exception as e:
        log(f"Error fetch_user_data: {e}")
    return None

def claim_daily_streak(cfg, data):
    if not cfg.get("auto_streak", True):
        return
    profile = data.get("profile", {})
    streak = profile.get("daily_streak_state", {})
    if streak.get("streak_reward_claimed_today", False):
        return

    url = f"{BASE_URL}/api/daily-streak"
    try:
        r = requests.post(url, headers=get_headers(cfg), json={"action": "claim"}, timeout=15)
        if r.status_code == 200:
            log("🎁 [STREAK] >> KLAIM HADIAH HARIAN BERHASIL! <<")
            return True
        elif r.status_code == 400 and "already_claimed" in r.text:
            pass
        elif r.status_code == 403 and "TURNSTILE" in r.text:
            log("🎁 [STREAK] Klaim streak tertunda (butuh Turnstile)")
        else:
            log(f"🎁 [STREAK] Klaim streak status (HTTP {r.status_code}): {r.text[:100]}")
    except Exception as e:
        log(f"Error claim_daily_streak: {e}")

def claim_egg_fragments(cfg, inventory):
    """Otomatis merakit 5 fragmen telur menjadi 1 telur baru secara gratis jika kuota tercukupi."""
    if not cfg.get("auto_claim_fragments", True) or not isinstance(inventory, dict):
        return
    for egg_type in ["mystery_egg", "golden_egg", "celestial_egg"]:
        frag_key = f"{egg_type}_fragment"
        count = inventory.get(frag_key, 0)
        if count >= 5:
            url = f"{BASE_URL}/api/eggs/claim-from-fragments"
            try:
                r = requests.post(url, headers=get_headers(cfg), json={"type": egg_type}, timeout=15)
                if r.status_code == 200:
                    res = r.json()
                    log(f"🥚 [EGG PUZZLE] >> BERHASIL MERAKIT 5 FRAGMEN MENJADI 1 {egg_type.upper()} GRATIS! <<")
                    inv_up = res.get("inventory", {})
                    inventory.update(inv_up)
                elif r.status_code == 400:
                    pass
                else:
                    log(f"🥚 [EGG PUZZLE] Status klaim {egg_type} (HTTP {r.status_code}): {r.text[:100]}")
            except Exception as e:
                log(f"Error claim_egg_fragments: {e}")

def apply_vital_action(cfg, monster_id, item_id, action="purchase", quantity=1):
    url = f"{BASE_URL}/api/vitals"
    payload = {
        "monsterId": monster_id,
        "itemId": item_id,
        "action": action,
        "quantity": quantity
    }
    try:
        r = requests.post(url, headers=get_headers(cfg), json=payload, timeout=15)
        if r.status_code == 200:
            return True, r.json()
        elif r.status_code == 403 and "TURNSTILE" in r.text:
            return "TURNSTILE_REQUIRED", r.json() if r.text else {}
        else:
            return False, r.text[:150]
    except Exception as e:
        return False, str(e)

def buy_store_consumable(cfg, item_id):
    """Membeli item consumable dari Toko Game resmi (/api/store) ke dalam inventori akun."""
    url = f"{BASE_URL}/api/store"
    payload = {
        "type": "consumable",
        "itemId": item_id,
        "paymentMethod": "lumis"
    }
    try:
        r = requests.post(url, headers=get_headers(cfg), json=payload, timeout=15)
        if r.status_code == 200:
            return True, r.json()
        elif r.status_code == 403 and "TURNSTILE" in r.text:
            return "TURNSTILE_REQUIRED", r.json() if r.text else {}
        else:
            return False, r.text[:150]
    except Exception as e:
        return False, str(e)

def execute_vital_fulfillment(cfg, m_id, m_name, vital_type, item_id, item_info, action, current_val, lumis_balance, inventory):
    """
    Eksekusi pemenuhan kebutuhan vitals:
    1. Jika action == 'buy_and_use', beli item dari store resmi terlebih dahulu ke inventori.
    2. Setelah ada di inventori, gunakan item secara instan (action == 'use_inventory').
    """
    item_name = item_info.get("name", item_id)
    val_inc = item_info.get("value", 15)

    if action == "buy_and_use":
        cost = item_info.get("price", 0)
        log(f"   🛒 Membeli {item_name} dari Toko Game ({cost:,} LUMIS)...")
        b_ok, b_res = buy_store_consumable(cfg, item_id)
        if b_ok is True:
            lumis_balance = b_res.get("newLumis", lumis_balance)
            inv_updates = b_res.get("inventoryUpdates", {})
            inventory.update(inv_updates)
            log(f"   >> PEMBELIAN {item_name} SUKSES! Saldo LUMIS: {lumis_balance:,} <<")
            time.sleep(1.0)
            action = "use_inventory"
        elif b_ok == "TURNSTILE_REQUIRED":
            log("   ⚠️ Verifikasi Cloudflare Turnstile diperlukan untuk pembelian di toko.")
            return "TURNSTILE_WAIT", current_val, lumis_balance
        else:
            log(f"   Gagal membeli di toko: {b_res}")
            return False, current_val, lumis_balance

    if action == "use_inventory":
        log(f"   ✨ Menggunakan {item_name} dari inventori untuk {m_name}...")
        ok, res = apply_vital_action(cfg, m_id, item_id, action="use_inventory")
        if ok is True:
            new_val = float(res.get("newVitalValue", current_val + val_inc))
            lumis_balance = res.get("newLumis", lumis_balance)
            inv_updates = res.get("inventoryUpdates", {})
            inventory.update(inv_updates)
            log(f"   >> BERHASIL MERAWAT {m_name}! {vital_type.upper()} Sekarang: {new_val:.1f}% (LUMIS: {lumis_balance:,}) <<")
            time.sleep(1.5)
            return True, new_val, lumis_balance
        elif ok == "TURNSTILE_REQUIRED":
            log("   ⚠️ Verifikasi Cloudflare Turnstile diperlukan untuk aksi vitals.")
            return "TURNSTILE_WAIT", current_val, lumis_balance
        else:
            log(f"   Gagal menggunakan item: {res}")
            return False, current_val, lumis_balance

    return False, current_val, lumis_balance

def manage_sleep_state(cfg, monster_id, action="wake_up"):
    url = f"{BASE_URL}/api/sleep"
    payload = {
        "monsterId": monster_id,
        "action": action
    }
    try:
        r = requests.post(url, headers=get_headers(cfg), json=payload, timeout=15)
        if r.status_code == 200:
            return True, r.json()
        elif r.status_code == 403 and "TURNSTILE" in r.text:
            return "TURNSTILE_REQUIRED", r.json() if r.text else {}
        else:
            return False, r.text[:150]
    except Exception as e:
        return False, str(e)

def run_pet_care_cycle():
    cfg = load_config()
    data = fetch_user_data(cfg)

    if data == "UNAUTHORIZED":
        log("Sesi expired. Menunggu generator me-refresh token...")
        return "WAIT_CONFIG"
    if data == "TURNSTILE_REQUIRED":
        return "TURNSTILE_WAIT"
    if not data or not isinstance(data, dict):
        log("Gagal mendapatkan data akun. Coba lagi siklus berikutnya.")
        return False

    profile = data.get("profile", {})
    monsters = data.get("monsters", [])
    inventory = data.get("inventory", {})
    lumis_balance = profile.get("lumis", 0)
    level = profile.get("level", 1)
    min_reserve = cfg.get("min_lumis_reserve", 100)

    log(f"🎮 Akun Level {level} | Saldo: {lumis_balance:,} LUMIS | Total Monsters: {len(monsters)}")

    # 1. Daily Check-in Streak & Egg Puzzle Fragments
    claim_daily_streak(cfg, data)
    claim_egg_fragments(cfg, inventory)

    # 2. Iterate each monster
    for m in monsters:
        if m.get("is_egg", False):
            continue
        m_id = m.get("_id")
        m_name = m.get("name", "Monster")
        vitals = m.get("vitals", {})
        food = float(vitals.get("food", 0.0))
        hygiene = float(vitals.get("hygiene", 0.0))
        energy = float(vitals.get("energy", 0.0))
        is_sleeping = m.get("is_sleeping", False)
        base_rate = m.get("base_production_rate", 0)
        personality = m.get("personality", "default")

        # Kapasitas tambang & masa aktif monster
        cap = m.get("capacity", {})
        total_cap = cap.get("total", 0)
        mined_cap = cap.get("mined", 0)
        cap_str = ""
        if total_cap > 0:
            pct = (mined_cap / total_cap) * 100.0
            rem = max(0, total_cap - mined_cap)
            cap_str = f" | ⛏️ Tambang: {mined_cap:,}/{total_cap:,} ({pct:.1f}%) [Sisa: {rem:,}]"

        log(f"🐾 [{m_name}] Status: {'💤 Tidur' if is_sleeping else '⚡ Bangun'} (Prod: {base_rate} LUMIS/h | Tipe: {personality.upper()}){cap_str}")
        log(f"   📊 Vitals: 🍎 Makan: {food:.1f}% | 🧼 Bersih: {hygiene:.1f}% | ⚡ Energi: {energy:.1f}%")

        # A. Memberi Makan (Feed) sampai mencapai batas threshold
        feed_threshold = float(cfg.get("feed_threshold", 80))
        if cfg.get("auto_feed", True):
            while food < feed_threshold:
                deficit = feed_threshold - food
                feed_item, item_info, action = select_best_vital_item("food", deficit, inventory, lumis_balance, min_reserve, profile=profile)
                if not feed_item:
                    cost = get_store_price("magic_apple", profile)
                    log(f"   ⏳ Saldo LUMIS ({lumis_balance:,}) belum cukup untuk membeli Magic Apple ({cost:,} LUMIS). Menambang {base_rate} LUMIS/h...")
                    break

                res_ok, food, lumis_balance = execute_vital_fulfillment(
                    cfg, m_id, m_name, "food", feed_item, item_info, action, food, lumis_balance, inventory
                )
                if res_ok == "TURNSTILE_WAIT":
                    return "TURNSTILE_WAIT"
                if not res_ok:
                    break

        # B. Membersihkan Badan (Clean / Bath) sampai mencapai batas threshold
        clean_threshold = float(cfg.get("clean_threshold", 80))
        if cfg.get("auto_clean", True):
            while hygiene < clean_threshold:
                deficit = clean_threshold - hygiene
                clean_item, item_info, action = select_best_vital_item("hygiene", deficit, inventory, lumis_balance, min_reserve, profile=profile)
                if not clean_item:
                    cost = get_store_price("fairy_bath", profile)
                    log(f"   ⏳ Saldo LUMIS ({lumis_balance:,}) belum cukup untuk membeli Fairy Bath ({cost:,} LUMIS). Menambang {base_rate} LUMIS/h...")
                    break

                res_ok, hygiene, lumis_balance = execute_vital_fulfillment(
                    cfg, m_id, m_name, "hygiene", clean_item, item_info, action, hygiene, lumis_balance, inventory
                )
                if res_ok == "TURNSTILE_WAIT":
                    return "TURNSTILE_WAIT"
                if not res_ok:
                    break

        # C. Manajemen Siklus Tidur & Energi Alami (Auto-Sleep / Wake Lifecycle)
        auto_sleep = cfg.get("auto_sleep", True)
        sleep_threshold = float(cfg.get("sleep_energy_threshold", 25))
        wake_threshold = float(cfg.get("wake_energy_threshold", 95))

        if is_sleeping:
            # Monster sedang tidur: cek apakah energinya sudah mencapai target bangun
            if energy >= wake_threshold and cfg.get("auto_wake", True):
                log(f"   ⚡ Energi {m_name} sudah terisi ({energy:.1f}% >= {wake_threshold}%). Membangunkan pet...")
                ok, res = manage_sleep_state(cfg, m_id, action="wake_up")
                if ok is True:
                    well_rested = res.get("well_rested_until", "Aktif")
                    xp_g = res.get("xp_gained", 0)
                    log(f"   >> {m_name} TELAH BANGUN! Mendapat +{xp_g} XP & Buff 'Well-Rested' (+25% Produksi) sampai {well_rested}! <<")
                    is_sleeping = False
                    energy = float(res.get("new_energy", energy))
                elif ok == "TURNSTILE_REQUIRED":
                    log("   ⚠️ Verifikasi Cloudflare Turnstile diperlukan untuk membangunkan pet.")
                    return "TURNSTILE_WAIT"
                else:
                    log(f"   Gagal membangunkan pet: {res}")
            else:
                log(f"   💤 {m_name} sedang tidur alami (Energi: {energy:.1f}% / Target: {wake_threshold}%). Pasif Dreamer: +50% energi/jam (Gratis 0 LUMIS)!")
        else:
            # Monster sedang bangun: periksa apakah energi sudah rendah untuk ditidurkan
            if auto_sleep and energy <= sleep_threshold:
                log(f"   🛌 Energi {m_name} rendah ({energy:.1f}% <= {sleep_threshold}%). Memulai tidur alami (Gratis + Buff Well-Rested)...")
                ok, res = manage_sleep_state(cfg, m_id, action="start_sleep")
                if ok is True:
                    log(f"   >> {m_name} MULAI TIDUR! Menghemat saldo LUMIS (0 Kopi) & memulihkan daya secara alami. <<")
                    is_sleeping = True
                elif ok == "TURNSTILE_REQUIRED":
                    log("   ⚠️ Verifikasi Cloudflare Turnstile diperlukan untuk menidurkan pet.")
                    return "TURNSTILE_WAIT"
                else:
                    log(f"   Gagal menidurkan pet: {res}")
            elif not auto_sleep and cfg.get("auto_coffee", False):
                # Fallback pembelian kopi jika auto_sleep sengaja dinonaktifkan
                coffee_threshold = float(cfg.get("coffee_threshold", 80))
                while energy < coffee_threshold:
                    deficit = coffee_threshold - energy
                    coffee_item, item_info, action = select_best_vital_item("energy", deficit, inventory, lumis_balance, min_reserve, profile=profile)
                    if not coffee_item:
                        cost = get_store_price("wizard_coffee", profile)
                        log(f"   ⏳ Saldo LUMIS ({lumis_balance:,}) belum cukup untuk membeli Wizard Coffee ({cost:,} LUMIS).")
                        break

                    res_ok, energy, lumis_balance = execute_vital_fulfillment(
                        cfg, m_id, m_name, "energy", coffee_item, item_info, action, energy, lumis_balance, inventory
                    )
                    if res_ok == "TURNSTILE_WAIT":
                        return "TURNSTILE_WAIT"
                    if not res_ok:
                        break
            else:
                log(f"   ⚡ {m_name} saat ini BANGUN dan aktif menambang {base_rate} LUMIS/h!")

        log(f"   📊 Vitals Terkini: 🍎 Makan: {food:.1f}% | 🧼 Bersih: {hygiene:.1f}% | ⚡ Energi: {energy:.1f}%")
        log(f"   🪙 Saldo Terkini : {lumis_balance:,} LUMIS")

    return True

def adaptive_sleep(seconds):
    initial_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
    start = time.time()
    while time.time() - start < seconds:
        time.sleep(2)
        if os.path.exists(CONFIG_PATH):
            current_mtime = os.path.getmtime(CONFIG_PATH)
            if current_mtime != initial_mtime:
                log(">> PERUBAHAN CONFIG.JSON TERDETEKSI! Memuat ulang konfigurasi & bangun seketika... <<")
                return True
    return False

def main():
    log("==================================================")
    log("🤖 DAEMON AUTO-FARM & PET CARE MONSTERLAND AKTIF")
    log(f"Lokasi Config : {CONFIG_PATH}")
    log(f"Lokasi Log    : {LOG_PATH}")
    log("==================================================")

    while True:
        try:
            status = run_pet_care_cycle()
            cfg = load_config()

            if status == "TURNSTILE_WAIT":
                log("💤 [Mode Siaga Cloudflare] Sesi membutuhkan Cloudflare Turnstile.")
                log("💡 Buka mini-app @monsterland_bot di Telegram sekali untuk memperbarui sesi,")
                log("   atau gunakan fitur Update Token di bot Telegram.")
                adaptive_sleep(300)
            elif status == "WAIT_CONFIG":
                log("💤 Menunggu token baru ditulis ke config.json...")
                adaptive_sleep(120)
            else:
                interval = cfg.get("check_interval_seconds", 300)
                jitter = random.randint(-15, 15)
                sleep_time = max(90, interval + jitter)
                log(f"💤 Siklus perawatan selesai. Tidur selama {sleep_time} detik (~{sleep_time//60} menit)...")
                adaptive_sleep(sleep_time)

        except Exception as e:
            log(f"Unhandled Exception: {e}")
            adaptive_sleep(60)

if __name__ == "__main__":
    main()
