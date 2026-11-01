#!/usr/bin/env python3
"""
promo_claimer.py - Daily Promo Code Auto-Claimer Daemon
Mengotomatisasi klaim kode promo harian, secret codes, dan teka-teki harian di berbagai bot:
1. StarNex Lottery (@lot_tery_bot) - Keypad 5 digit Bulls & Cows
2. PaidZ (@PAlDZ_BOT) - Kode tugas reward mikro
3. SoftUSDT (@Softusdtbot) - Kode promo komunitas
4. Universe (@universe_mainbot) - Kode promo mingguan & riddle
5. Arsitektur modular yang dapat didaftarkan kode baru kapan saja via CLI / JSON
"""

import os
import sys
import time
import json
import re
import asyncio
import argparse
from datetime import datetime
from telethon import TelegramClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(BASE_DIR, "auth_generator", "tg_session")
CODES_FILE = os.path.join(BASE_DIR, "maintenance", "promo_codes.json")
REPORT_FILE = os.path.join(BASE_DIR, "maintenance", "promo_claimer_report.json")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def load_codes():
    if os.path.exists(CODES_FILE):
        try:
            with open(CODES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"⚠️ Gagal membaca {CODES_FILE}: {e}")
    return {"updated_at": "", "bots": {}}

def save_codes(data):
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(CODES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"⚠️ Gagal menyimpan {CODES_FILE}: {e}")

# ==================== AUTO SCRAPER: TELEGRAM CHANNELS ====================

async def auto_scrape_channels(client):
    log("==================================================")
    log("🛰️ [Promo Scraper] Memindai channel komunitas untuk kode terbaru...")
    log("==================================================")
    codes_data = load_codes()
    bots = codes_data.get("bots", {})
    scraped_count = 0

    # 1. Scrape @playing_web3 (Playing WEB3 Official)
    try:
        ent_pw = await client.get_entity("playing_web3")
        msgs_pw = await client.get_messages(ent_pw, limit=20)
        for m in msgs_pw:
            txt = m.text or ""

            # StarNex Daily Secret Code
            sn_m = re.search(r"lot_tery_bot.*?daily secret code:.*?`(\d{5})`", txt, re.DOTALL)
            if sn_m and "starnex" in bots:
                new_c = sn_m.group(1).strip()
                if bots["starnex"].get("active_code") != new_c:
                    log(f"   🎯 [StarNex] Ditemukan kode baru dari @playing_web3: {new_c}")
                    bots["starnex"]["active_code"] = new_c
                    scraped_count += 1

            # Universe Daily Riddle
            rid_m = re.search(r"daily riddle answer.*?`([^`]+)`", txt, re.DOTALL)
            if rid_m and "universe" in bots:
                new_r = rid_m.group(1).strip()
                if bots["universe"].get("riddle_answer") != new_r:
                    log(f"   🎯 [Universe] Ditemukan riddle baru: '{new_r}'")
                    bots["universe"]["riddle_answer"] = new_r
                    scraped_count += 1

            # Universe Promo Code
            up_m = re.search(r"Exclusive promo code.*?`([A-Z0-9]{10,})`", txt, re.DOTALL)
            if up_m and "universe" in bots:
                new_up = up_m.group(1).strip()
                if new_up not in bots["universe"].get("codes", []):
                    log(f"   🎯 [Universe] Ditemukan promo baru: '{new_up}'")
                    bots["universe"]["codes"] = [new_up]
                    scraped_count += 1

            # PaidZ claim codes
            pz_codes = re.findall(r"`(PWEB3-[A-Z0-9]+)`", txt)
            if pz_codes and "paidz" in bots:
                existing = set(bots["paidz"].get("codes", []))
                for c in pz_codes:
                    if c not in existing:
                        log(f"   🎯 [PaidZ] Ditemukan kode tugas baru: '{c}'")
                        existing.add(c)
                        scraped_count += 1
                bots["paidz"]["codes"] = list(existing)

    except Exception as e:
        log(f"   ⚠️ Gagal memindai @playing_web3: {e}")

    # 2. Scrape @cryptoearing1 (Crypto Lover ☺️)
    try:
        ent_cl = await client.get_entity("cryptoearing1")
        msgs_cl = await client.get_messages(ent_cl, limit=20)
        for m in msgs_cl:
            txt = m.text or ""
            # SoftUSDT early bird claim codes
            su_m = re.search(r"Claim Code \d+:\s*`([A-Z0-9]{6,10})`", txt)
            if su_m and "softusdt" in bots:
                su_code = su_m.group(1).strip()
                if su_code not in bots["softusdt"].get("codes", []):
                    log(f"   🎯 [SoftUSDT] Ditemukan kode baru dari @cryptoearing1: '{su_code}'")
                    bots["softusdt"]["codes"] = [su_code]
                    scraped_count += 1

    except Exception as e:
        log(f"   ⚠️ Gagal memindai @cryptoearing1: {e}")

    if scraped_count > 0:
        save_codes(codes_data)
        log(f"✅ Scraping sukses: {scraped_count} kode baru berhasil diupdate ke promo_codes.json!\n")
    else:
        log("ℹ️ Scraping selesai: Seluruh kode promo sudah ter-sinkronisasi dengan pesan terbaru.\n")

    return codes_data

# ==================== HANDLER: STARNEX LOTTERY ====================

async def handle_starnex(client, bot_cfg):
    log("--------------------------------------------------")
    log("🎰 [Promo Claimer] Menjalankan StarNex Lottery...")
    log("--------------------------------------------------")
    bot_user = bot_cfg.get("bot_username", "lot_tery_bot")
    code = bot_cfg.get("active_code", "29710")

    try:
        bot = await client.get_entity(bot_user)
        # Buka menu free spins
        await client.send_message(bot, "🎁 Free spins")
        await asyncio.sleep(2.5)

        msgs = await client.get_messages(bot, limit=3)
        target_msg = None
        for m in msgs:
            if m.reply_markup:
                target_msg = m
                break

        if not target_msg:
            log("❌ Tidak ada tombol menu Free spins ditemukan.")
            return {"status": "failed", "error": "Menu Free spins not found"}

        # Cari tombol "🧩 Guess the code"
        clicked = False
        for r_idx, row in enumerate(target_msg.reply_markup.rows):
            for c_idx, b in enumerate(row.buttons):
                if "Guess the code" in b.text:
                    log("   ↳ Menemukan tombol '🧩 Guess the code', membuka keypad...")
                    await target_msg.click(r_idx, c_idx)
                    clicked = True
                    break
            if clicked:
                break

        if not clicked:
            log("⚠️ Tombol 'Guess the code' tidak tersedia saat ini.")
            return {"status": "skipped", "reason": "Tombol Guess the code tidak tersedia"}

        await asyncio.sleep(3.0)

        # Ambil pesan keypad
        km_list = await client.get_messages(bot, limit=1)
        if not km_list or not km_list[0].reply_markup:
            log("⚠️ Keypad tidak terbuka.")
            return {"status": "failed", "error": "Keypad tidak terbuka"}

        km = km_list[0]
        log(f"   ↳ Keypad aktif. Menginput kode rahasia: {code}...")

        async def press_keypad(key_char):
            nonlocal km
            # Re-fetch pesan untuk memastikan state markup sinkron
            refetched = await client.get_messages(bot, ids=[km.id])
            if refetched and refetched[0].reply_markup:
                km = refetched[0]
                for r_idx, row in enumerate(km.reply_markup.rows):
                    for c_idx, b in enumerate(row.buttons):
                        if b.text.strip() == key_char:
                            await km.click(r_idx, c_idx)
                            await asyncio.sleep(1.8)
                            return True
            return False

        # Input tiap digit
        for d in code:
            success = await press_keypad(d)
            if not success:
                log(f"   ⚠️ Gagal menekan digit {d}")

        # Tekan "Проверить" (Verifikasi)
        log("   ↳ Mengirim verifikasi (Проверить)...")
        await press_keypad("Проверить")
        await asyncio.sleep(2.5)

        # Baca respons akhir
        final_msgs = await client.get_messages(bot, limit=1)
        resp_text = final_msgs[0].text if final_msgs else "No reply"
        first_line = resp_text.split("\n")[0] if resp_text else ""
        log(f"   🎉 Respon StarNex: {first_line}")

        return {
            "status": "success",
            "bot": "starnex",
            "code_used": code,
            "response": resp_text[:200]
        }
    except Exception as e:
        log(f"❌ Exception StarNex: {e}")
        return {"status": "error", "error": str(e)}

# ==================== HANDLER: PAIDZ TASKS ====================

async def handle_paidz(client, bot_cfg):
    log("--------------------------------------------------")
    log("💰 [Promo Claimer] Menjalankan PaidZ Tasks...")
    log("--------------------------------------------------")
    bot_user = bot_cfg.get("bot_username", "PAlDZ_BOT")
    codes = bot_cfg.get("codes", ["PWEB3-CMZC", "PWEB3-3WK5"])

    results = []
    try:
        bot = await client.get_entity(bot_user)
        for code in codes:
            log(f"   ↳ Mencoba klaim kode PaidZ: '{code}'...")
            await client.send_message(bot, f"/code {code}")
            await asyncio.sleep(2.5)
            msgs = await client.get_messages(bot, limit=2)
            reply = msgs[0].text if msgs and msgs[0].sender_id != 1234567890 else "No response"
            log(f"      Respon: {reply[:100]}")
            results.append({"code": code, "reply": reply[:100]})
            await asyncio.sleep(1.5)

        return {"status": "success", "bot": "paidz", "details": results}
    except Exception as e:
        log(f"❌ Exception PaidZ: {e}")
        return {"status": "error", "error": str(e)}

# ==================== HANDLER: SOFTUSDT ====================

async def handle_softusdt(client, bot_cfg):
    log("--------------------------------------------------")
    log("💵 [Promo Claimer] Menjalankan SoftUSDT...")
    log("--------------------------------------------------")
    bot_user = bot_cfg.get("bot_username", "Softusdtbot")
    codes = bot_cfg.get("codes", ["8D7YEUUE"])

    results = []
    try:
        bot = await client.get_entity(bot_user)
        for code in codes:
            log(f"   ↳ Mengirim kode promo SoftUSDT: '{code}'...")
            await client.send_message(bot, f"/claim {code}")
            await asyncio.sleep(2.0)
            await client.send_message(bot, code)
            await asyncio.sleep(2.0)
            msgs = await client.get_messages(bot, limit=2)
            reply = msgs[0].text if msgs and msgs[0].sender_id != 1234567890 else "Terkirim ke bot"
            results.append({"code": code, "status": "submitted", "reply": reply[:100]})

        return {"status": "success", "bot": "softusdt", "details": results}
    except Exception as e:
        log(f"❌ Exception SoftUSDT: {e}")
        return {"status": "error", "error": str(e)}

# ==================== HANDLER: UNIVERSE ====================

async def handle_universe(client, bot_cfg):
    log("--------------------------------------------------")
    log("🌀 [Promo Claimer] Menjalankan Universe...")
    log("--------------------------------------------------")
    bot_user = bot_cfg.get("bot_username", "universe_mainbot")
    codes = bot_cfg.get("codes", ["AMBDH0RYY4VBYH2"])
    riddle = bot_cfg.get("riddle_answer", "oort cloud")

    results = []
    try:
        bot = await client.get_entity(bot_user)
        # 1. Kirim Riddle
        if riddle:
            log(f"   ↳ Mengirim jawaban Riddle: '{riddle}'...")
            await client.send_message(bot, f"/riddle {riddle}")
            await asyncio.sleep(2.0)
            await client.send_message(bot, riddle)
            await asyncio.sleep(2.0)
            results.append({"type": "riddle", "answer": riddle, "status": "submitted"})

        # 2. Kirim Promo Codes
        for code in codes:
            log(f"   ↳ Mengirim kode promo Universe: '{code}'...")
            await client.send_message(bot, f"/code {code}")
            await asyncio.sleep(2.0)
            results.append({"type": "promo", "code": code, "status": "submitted"})

        return {"status": "success", "bot": "universe", "details": results}
    except Exception as e:
        log(f"❌ Exception Universe: {e}")
        return {"status": "error", "error": str(e)}

# ==================== DISPATCHER & CLI ====================

HANDLERS = {
    "starnex": handle_starnex,
    "paidz": handle_paidz,
    "softusdt": handle_softusdt,
    "universe": handle_universe
}

async def run_claimer(target_bot=None, skip_scrape=False):
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        log("❌ Sesi Telegram tidak terotorisasi.")
        await client.disconnect()
        return

    me = await client.get_me()
    log(f"👤 Otorisasi Telegram: {me.first_name} (@{me.username}) ID: {me.id}\n")

    # 1. Jalankan auto-scraper untuk menarik kode terkini dari channel komunitas
    if not skip_scrape:
        codes_data = await auto_scrape_channels(client)
    else:
        codes_data = load_codes()

    bots = codes_data.get("bots", {})

    report_results = []

    targets = [target_bot] if target_bot else list(bots.keys())

    for b_key in targets:
        b_cfg = bots.get(b_key)
        if not b_cfg:
            log(f"⚠️ Bot '{b_key}' tidak terdaftar di {CODES_FILE}")
            continue

        if not b_cfg.get("enabled", True):
            log(f"⏩ Bot '{b_key}' dinonaktifkan, dilewati.")
            continue

        handler = HANDLERS.get(b_key)
        if handler:
            res = await handler(client, b_cfg)
            res["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_results.append(res)
            # Update last claimed timestamp
            b_cfg["last_claimed"] = res["timestamp"]
            b_cfg["last_status"] = res.get("status", "completed")
        else:
            log(f"⚠️ Handler untuk '{b_key}' belum diimplementasikan.")

        await asyncio.sleep(2.0)

    await client.disconnect()

    # Simpan status terbaru ke promo_codes.json
    save_codes(codes_data)

    # Simpan laporan
    final_report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": report_results
    }
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    log("\n" + "=" * 60)
    log("🎉 SIKLUS DAILY PROMO CODE CLAIMER SELESAI!")
    log(f"📄 Laporan tersimpan di: {REPORT_FILE}")
    log("=" * 60)

def print_status():
    codes_data = load_codes()
    bots = codes_data.get("bots", {})
    print("\n" + "=" * 75)
    print(f"📋 DAFTAR KODE PROMO & STATUS (Pembaruan Terakhir: {codes_data.get('updated_at', 'N/A')})")
    print("=" * 75)
    print(f"{'BOT':<12} | {'USERNAME':<16} | {'STATUS':<9} | {'TERAKHIR KLAIM':<19} | {'KODE AKTIF'}")
    print("-" * 75)
    for k, v in bots.items():
        enabled_str = "AKTIF" if v.get("enabled") else "OFF"
        last = v.get("last_claimed") or "Belum pernah"
        code_str = v.get("active_code") or ", ".join(v.get("codes", []))
        print(f"{k:<12} | @{v.get('bot_username'):<15} | {enabled_str:<9} | {last:<19} | {code_str}")
    print("=" * 75 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Daily Promo Code Auto-Claimer Daemon")
    parser.add_argument("--all", action="store_true", help="Jalankan klaim ke seluruh bot yang aktif")
    parser.add_argument("--bot", type=str, help="Jalankan klaim hanya untuk bot tertentu (starnex, paidz, softusdt, universe)")
    parser.add_argument("--status", action="store_true", help="Tampilkan daftar bot, kode promo, dan status klaim")
    parser.add_argument("--scrape-only", action="store_true", help="Hanya jalankan pemindaian channel komunitas untuk update kode tanpa eksekusi klaim")
    parser.add_argument("--skip-scrape", action="store_true", help="Lewati pemindaian channel dan langsung klaim kode yang ada")
    parser.add_argument("--set-code", nargs=2, metavar=("BOT", "CODE"), help="Perbarui kode promo harian (contoh: --set-code starnex 29710)")

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.scrape_only:
        async def do_scrape():
            client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                await auto_scrape_channels(client)
            await client.disconnect()
        asyncio.run(do_scrape())
        print_status()
        return

    if args.set_code:
        bot_name, new_code = args.set_code
        codes_data = load_codes()
        if bot_name in codes_data.get("bots", {}):
            if "active_code" in codes_data["bots"][bot_name]:
                codes_data["bots"][bot_name]["active_code"] = new_code
            else:
                codes_data["bots"][bot_name]["codes"] = [new_code]
            save_codes(codes_data)
            print(f"✅ Berhasil memperbarui kode promo untuk '{bot_name}' menjadi: {new_code}")
        else:
            print(f"❌ Bot '{bot_name}' not found di {CODES_FILE}")
        return

    if args.bot:
        asyncio.run(run_claimer(target_bot=args.bot, skip_scrape=args.skip_scrape))
    elif args.all:
        asyncio.run(run_claimer(skip_scrape=args.skip_scrape))
    else:
        # Default run all with auto-scrape if called directly or by systemd
        asyncio.run(run_claimer(skip_scrape=args.skip_scrape))

if __name__ == "__main__":
    main()
