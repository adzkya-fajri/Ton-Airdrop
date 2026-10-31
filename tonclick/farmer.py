#!/usr/bin/env python3
"""
TON Click Robot (@TonClickRobot) Auto-Farmer Daemon
Automates Micro-Task & PTC (Paid-To-Click) tasks:
1. Message Bots (Start sponsor bots & forward verification message)
2. Join Chats (Join sponsor channels/groups & track retention before leaving)
3. Visit Sites (Fetch web task URLs with simulated browser agent)
4. Balance tracking & optional instant FaucetPay withdrawal

Payout: Real TON cryptocurrency
"""

import os
import sys
import time
import json
import random
import re
import asyncio
from datetime import datetime, timedelta
import urllib.parse
import requests
from telethon import TelegramClient, functions, types, errors

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
RETENTION_FILE = os.path.join(BASE_DIR, "retention.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
SESSION_FILE = os.path.join(BASE_DIR, "tonclick_session")

API_ID = 30234133
API_HASH = "142e316c8fce3f9a94b655a3d3593aee"

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
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Gagal membaca config.json: {e}")
    return {
        "bot_username": "TonClickRobot",
        "cycle_interval_seconds": 900,
        "max_join_tasks_per_cycle": 5,
        "max_bot_tasks_per_cycle": 5,
        "retention_hours": 72,
        "auto_cleanup_old_channels": True,
        "faucetpay_email": "",
        "auto_withdraw_faucetpay": False
    }

def load_retention():
    if os.path.exists(RETENTION_FILE):
        try:
            with open(RETENTION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_retention(data):
    try:
        with open(RETENTION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"Gagal menyimpan retention.json: {e}")

async def cleanup_retention(client, retention_hours):
    retention = load_retention()
    if not retention:
        return
    now = datetime.now()
    to_delete = []
    
    for ch_ident, join_time_str in list(retention.items()):
        try:
            join_time = datetime.fromisoformat(join_time_str)
            if now - join_time >= timedelta(hours=retention_hours):
                log(f"[Retention] Channel '{ch_ident}' telah melewati masa retensi {retention_hours}h. Meninggalkan channel...")
                try:
                    entity = await client.get_entity(ch_ident)
                    await client(functions.channels.LeaveChannelRequest(entity))
                    log(f"[Retention] Berhasil meninggalkan channel '{ch_ident}'.")
                except Exception as ex:
                    log(f"[Retention] Peringatan saat meninggalkan '{ch_ident}': {ex}")
                to_delete.append(ch_ident)
                await asyncio.sleep(random.uniform(4.0, 7.0))
        except Exception as e:
            log(f"[Retention] Error evaluasi '{ch_ident}': {e}")
            
    if to_delete:
        for k in to_delete:
            retention.pop(k, None)
        save_retention(retention)

async def check_balance(client, bot):
    try:
        await client.send_message(bot, "/balance")
        await asyncio.sleep(2.0)
        msgs = await client.get_messages(bot, limit=2)
        for m in reversed(msgs):
            if m.sender_id != (await client.get_me()).id and "balance" in m.text.lower():
                log(f"[Balance] {m.text.strip()}")
                return m.text.strip()
    except Exception as e:
        log(f"[Balance] Gagal mengambil saldo: {e}")
    return ""

async def withdraw_faucetpay(email, amount=None):
    """Melakukan proses penarikan saldo TON ke akun FaucetPay via @TonClickRobot."""
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return False, "Sesi Telegram tidak terotorisasi."

    try:
        bot = await client.get_entity("TonClickRobot")
        
        # Ambil saldo dan cek batas minimum WD (0.001 TON)
        await client.send_message(bot, "/balance")
        await asyncio.sleep(2.0)
        bal_msgs = await client.get_messages(bot, limit=2)
        bal_val = 0.0
        for m in reversed(bal_msgs):
            if "balance" in m.text.lower():
                match = re.search(r"([\d.]+)\s*TON", m.text)
                if match:
                    bal_val = float(match.group(1))
                break

        if bal_val < 0.001:
            await client.disconnect()
            return False, f"Saldo ({bal_val:.7f} TON) belum memenuhi minimum FaucetPay (0.001 TON)."

        # Kirim permintaan penarikan FaucetPay
        await client.send_message(bot, "/withdraw")
        await asyncio.sleep(2.0)
        await client.send_message(bot, "📤 FaucetPay Withdrawal")
        await asyncio.sleep(2.0)

        msgs = await client.get_messages(bot, limit=1)
        if not msgs or "email" not in msgs[0].text.lower():
            await client.send_message(bot, "🔙 Back")
            await client.disconnect()
            return False, f"Respon tidak sesuai: {msgs[0].text if msgs else 'Kosong'}"

        # Kirim email FaucetPay
        await client.send_message(bot, email.strip())
        await asyncio.sleep(2.5)

        msgs = await client.get_messages(bot, limit=1)
        resp_text = msgs[0].text if msgs else ""

        # Jika diminta nominal, kirim jumlah
        if any(w in resp_text.lower() for w in ["amount", "how much", "enter"]):
            wd_amt_str = f"{amount:.7f}" if (amount and amount <= bal_val) else f"{bal_val:.7f}"
            await client.send_message(bot, wd_amt_str)
            await asyncio.sleep(2.5)
            msgs = await client.get_messages(bot, limit=1)
            resp_text = msgs[0].text if msgs else ""

        # Klik tombol konfirmasi bila tersedia
        if msgs and msgs[0].reply_markup and hasattr(msgs[0].reply_markup, "rows"):
            for row in msgs[0].reply_markup.rows:
                for b in row.buttons:
                    if any(w in b.text.lower() for w in ["confirm", "yes", "ya", "submit"]):
                        try:
                            await msgs[0].click(text=b.text)
                            await asyncio.sleep(2.5)
                            msgs = await client.get_messages(bot, limit=1)
                            resp_text = msgs[0].text if msgs else ""
                        except Exception:
                            pass
                        break

        # Reset ke menu utama
        await client.send_message(bot, "🔙 Back")
        await asyncio.sleep(1.0)
        await client.disconnect()

        log(f"[Withdraw] Hasil WD ke {email}: {resp_text}")
        return True, resp_text

    except Exception as e:
        log(f"[Withdraw] Error: {e}")
        try:
            await client.send_message(bot, "🔙 Back")
            await client.disconnect()
        except Exception:
            pass
        return False, f"Gagal saat penarikan: {e}"

async def withdraw_direct_ton(wallet_address, amount=None):
    """Melakukan proses penarikan saldo TON langsung ke alamat wallet on-chain TON (Direct)."""
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return False, "Sesi Telegram tidak terotorisasi."

    try:
        bot = await client.get_entity("TonClickRobot")
        
        # Ambil saldo dan cek batas minimum WD
        await client.send_message(bot, "/balance")
        await asyncio.sleep(2.0)
        bal_msgs = await client.get_messages(bot, limit=2)
        bal_val = 0.0
        for m in reversed(bal_msgs):
            if "balance" in m.text.lower():
                match = re.search(r"([\d.]+)\s*TON", m.text)
                if match:
                    bal_val = float(match.group(1))
                break

        if bal_val < 0.1:
            await client.disconnect()
            return False, f"Saldo ({bal_val:.7f} TON) belum memenuhi minimum Direct (0.1 TON)."

        # Kirim permintaan penarikan Direct
        await client.send_message(bot, "/withdraw")
        await asyncio.sleep(2.0)
        await client.send_message(bot, "📤 Direct Withdrawal")
        await asyncio.sleep(2.0)

        msgs = await client.get_messages(bot, limit=1)
        resp_text = msgs[0].text if msgs else ""

        if "not enough" in resp_text.lower():
            await client.send_message(bot, "🔙 Back")
            await client.disconnect()
            return False, f"Server menolak: {resp_text}"

        # Kirim alamat wallet TON
        await client.send_message(bot, wallet_address.strip())
        await asyncio.sleep(2.5)

        msgs = await client.get_messages(bot, limit=1)
        resp_text = msgs[0].text if msgs else ""

        # Jika diminta nominal, kirim jumlah
        if any(w in resp_text.lower() for w in ["amount", "how much", "enter"]):
            wd_amt_str = f"{amount:.7f}" if (amount and amount <= bal_val) else f"{bal_val:.7f}"
            await client.send_message(bot, wd_amt_str)
            await asyncio.sleep(2.5)
            msgs = await client.get_messages(bot, limit=1)
            resp_text = msgs[0].text if msgs else ""

        # Klik tombol konfirmasi bila tersedia
        if msgs and msgs[0].reply_markup and hasattr(msgs[0].reply_markup, "rows"):
            for row in msgs[0].reply_markup.rows:
                for b in row.buttons:
                    if any(w in b.text.lower() for w in ["confirm", "yes", "ya", "submit"]):
                        try:
                            await msgs[0].click(text=b.text)
                            await asyncio.sleep(2.5)
                            msgs = await client.get_messages(bot, limit=1)
                            resp_text = msgs[0].text if msgs else ""
                        except Exception:
                            pass
                        break

        # Reset ke menu utama
        await client.send_message(bot, "🔙 Back")
        await asyncio.sleep(1.0)
        await client.disconnect()

        log(f"[Direct-WD] Hasil WD ke {wallet_address}: {resp_text}")
        return True, resp_text

    except Exception as e:
        log(f"[Direct-WD] Error: {e}")
        try:
            await client.send_message(bot, "🔙 Back")
            await client.disconnect()
        except Exception:
            pass
        return False, f"Gagal saat penarikan Direct: {e}"

async def withdraw_cryptobot(amount=None):
    """Melakukan proses penarikan saldo TON ke @CryptoBot via @TonClickRobot."""
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return False, "Sesi Telegram tidak terotorisasi."

    try:
        bot = await client.get_entity("TonClickRobot")
        
        # Ambil saldo dan cek batas minimum WD (1.0 TON)
        await client.send_message(bot, "/balance")
        await asyncio.sleep(2.0)
        bal_msgs = await client.get_messages(bot, limit=2)
        bal_val = 0.0
        for m in reversed(bal_msgs):
            if "balance" in m.text.lower():
                match = re.search(r"([\d.]+)\s*TON", m.text)
                if match:
                    bal_val = float(match.group(1))
                break

        if bal_val < 1.0:
            await client.disconnect()
            return False, f"Saldo ({bal_val:.7f} TON) belum memenuhi minimum CryptoBot (1.0 TON)."

        # Kirim permintaan penarikan CryptoBot
        await client.send_message(bot, "/withdraw")
        await asyncio.sleep(2.0)
        await client.send_message(bot, "📤 CryptoBot Withdrawal")
        await asyncio.sleep(2.0)

        msgs = await client.get_messages(bot, limit=1)
        resp_text = msgs[0].text if msgs else ""

        if "not enough" in resp_text.lower():
            await client.send_message(bot, "🔙 Back")
            await client.disconnect()
            return False, f"Server menolak: {resp_text}"

        # Jika diminta nominal, kirim jumlah
        if any(w in resp_text.lower() for w in ["amount", "how much", "enter"]):
            wd_amt_str = f"{amount:.7f}" if (amount and amount <= bal_val) else f"{bal_val:.7f}"
            await client.send_message(bot, wd_amt_str)
            await asyncio.sleep(2.5)
            msgs = await client.get_messages(bot, limit=1)
            resp_text = msgs[0].text if msgs else ""

        # Klik tombol konfirmasi bila tersedia
        if msgs and msgs[0].reply_markup and hasattr(msgs[0].reply_markup, "rows"):
            for row in msgs[0].reply_markup.rows:
                for b in row.buttons:
                    if any(w in b.text.lower() for w in ["confirm", "yes", "ya", "submit"]):
                        try:
                            await msgs[0].click(text=b.text)
                            await asyncio.sleep(2.5)
                            msgs = await client.get_messages(bot, limit=1)
                            resp_text = msgs[0].text if msgs else ""
                        except Exception:
                            pass
                        break

        # Reset ke menu utama
        await client.send_message(bot, "🔙 Back")
        await asyncio.sleep(1.0)
        await client.disconnect()

        log(f"[CryptoBot-WD] Hasil WD ke @CryptoBot: {resp_text}")
        return True, resp_text

    except Exception as e:
        log(f"[CryptoBot-WD] Error: {e}")
        try:
            await client.send_message(bot, "🔙 Back")
            await client.disconnect()
        except Exception:
            pass
        return False, f"Gagal saat penarikan CryptoBot: {e}"

async def do_join_chats(client, bot, max_tasks=5):
    log("[Task: Join Chats] Memeriksa tugas gabung channel...")
    tasks_done = 0
    retention = load_retention()

    while tasks_done < max_tasks:
        try:
            await client.send_message(bot, "📣 Join chats")
            await asyncio.sleep(random.uniform(2.5, 3.5))

            msgs = await client.get_messages(bot, limit=1)
            if not msgs:
                break
            msg = msgs[0]

            if "no new ads available" in msg.text.lower():
                log("[Task: Join Chats] Tidak ada iklan/tugas channel baru.")
                break

            channel_url = None
            joined_btn = None
            skip_btn = None

            if msg.reply_markup and hasattr(msg.reply_markup, "rows"):
                for row in msg.reply_markup.rows:
                    for b in row.buttons:
                        btn_url = getattr(b, "url", None) or getattr(getattr(b, "type", None), "url", None)
                        if btn_url and ("t.me" in btn_url or "telegram.me" in btn_url):
                            channel_url = btn_url
                        if b.text == "✅ Joined":
                            joined_btn = b
                        if "skip" in b.text.lower():
                            skip_btn = b

            if not channel_url or not joined_btn:
                # Coba cari URL dari teks
                urls = re.findall(r"https?://t\.me/[^\s]+", msg.text)
                if urls:
                    channel_url = urls[0]

            if not channel_url or not joined_btn:
                log("[Task: Join Chats] Format tugas tidak dikenali atau tidak ada link channel. Lewati.")
                if skip_btn:
                    await msg.click(data=getattr(getattr(skip_btn, "type", None), "data", None))
                    await asyncio.sleep(2.0)
                break

            log(f"[Task: Join Chats] Bergabung ke target: {channel_url}")
            ch_clean = channel_url.split("?")[0].replace("https://t.me/", "").replace("https://telegram.me/", "").replace("@", "").strip("/")

            joined_ok = False
            try:
                if ch_clean.startswith("+") or "joinchat" in channel_url:
                    invite_hash = channel_url.split("+")[-1].split("joinchat/")[-1]
                    await client(functions.messages.ImportChatInviteRequest(invite_hash))
                else:
                    target_entity = await client.get_entity(ch_clean)
                    await client(functions.channels.JoinChannelRequest(target_entity))
                joined_ok = True
                retention[ch_clean] = datetime.now().isoformat()
                save_retention(retention)
                log(f"[Task: Join Chats] Sukses masuk channel: {ch_clean}")
            except errors.FloodWaitError as fwe:
                log(f"[Task: Join Chats] Terkena FloodWait {fwe.seconds}s dari Telegram! Menghentikan task channel.")
                break
            except errors.UserAlreadyParticipantError:
                joined_ok = True
                log(f"[Task: Join Chats] Sudah menjadi anggota {ch_clean}.")
            except Exception as e:
                log(f"[Task: Join Chats] Gagal join channel {channel_url}: {e}")
                if skip_btn:
                    await msg.click(data=getattr(getattr(skip_btn, "type", None), "data", None))
                    await asyncio.sleep(2.0)
                continue

            if joined_ok:
                await asyncio.sleep(random.uniform(2.5, 4.0))
                # Klik tombol Joined
                try:
                    await client(functions.messages.GetBotCallbackAnswerRequest(
                        peer=bot,
                        msg_id=msg.id,
                        data=joined_btn.type.data
                    ))
                except Exception:
                    await msg.click(data=joined_btn.type.data)

                await asyncio.sleep(random.uniform(2.5, 3.5))
                res_msgs = await client.get_messages(bot, limit=2)
                for r in reversed(res_msgs):
                    if "earned" in r.text.lower():
                        log(f"[Task: Join Chats] 🎉 Reward didapat: {r.text.strip()}")
                        tasks_done += 1
                        break

            await asyncio.sleep(random.uniform(3.0, 5.0))

        except Exception as e:
            log(f"[Task: Join Chats] Error: {e}")
            break

    log(f"[Task: Join Chats] Selesai ({tasks_done} tugas diselesaikan).")

async def do_message_bots(client, bot, max_tasks=5):
    log("[Task: Message Bots] Memeriksa tugas kirim pesan bot...")
    tasks_done = 0

    while tasks_done < max_tasks:
        try:
            await client.send_message(bot, "🤖 Message Bots")
            await asyncio.sleep(random.uniform(2.5, 3.5))

            msgs = await client.get_messages(bot, limit=1)
            if not msgs:
                break
            msg = msgs[0]

            if "no new ads available" in msg.text.lower():
                log("[Task: Message Bots] Tidak ada iklan/tugas bot baru.")
                break

            bot_url = None
            skip_btn = None

            if msg.reply_markup and hasattr(msg.reply_markup, "rows"):
                for row in msg.reply_markup.rows:
                    for b in row.buttons:
                        btn_url = getattr(b, "url", None) or getattr(getattr(b, "type", None), "url", None)
                        if btn_url and "t.me" in btn_url:
                            bot_url = btn_url
                        if "skip" in b.text.lower():
                            skip_btn = b

            if not bot_url:
                log("[Task: Message Bots] Tidak menemukan link bot. Lewati.")
                if skip_btn:
                    await msg.click(data=getattr(getattr(skip_btn, "type", None), "data", None))
                    await asyncio.sleep(2.0)
                break

            parsed = urllib.parse.urlparse(bot_url)
            target_username = parsed.path.strip("/")
            start_param = urllib.parse.parse_qs(parsed.query).get("start", [None])[0]

            log(f"[Task: Message Bots] Menghubungi target bot: @{target_username} (start: {start_param})")
            target_entity = await client.get_entity(target_username)

            if start_param:
                await client.send_message(target_entity, f"/start {start_param}")
            else:
                await client.send_message(target_entity, "/start")

            await asyncio.sleep(random.uniform(2.5, 4.0))

            reply_msgs = await client.get_messages(target_entity, limit=1)
            if not reply_msgs:
                log(f"[Task: Message Bots] Target bot @{target_username} tidak membalas. Melewati...")
                if skip_btn:
                    await msg.click(data=getattr(getattr(skip_btn, "type", None), "data", None))
                    await asyncio.sleep(2.0)
                continue

            target_reply = reply_msgs[0]
            log(f"[Task: Message Bots] Mem-forward pesan id {target_reply.id} dari @{target_username} ke TonClickRobot...")
            await client.forward_messages(bot, target_reply)

            await asyncio.sleep(random.uniform(2.5, 4.0))
            confirm_msgs = await client.get_messages(bot, limit=2)
            for cm in reversed(confirm_msgs):
                if "earned" in cm.text.lower():
                    log(f"[Task: Message Bots] 🎉 Reward didapat: {cm.text.strip()}")
                    tasks_done += 1
                    break

            await asyncio.sleep(random.uniform(3.0, 5.0))

        except Exception as e:
            log(f"[Task: Message Bots] Error: {e}")
            break

    log(f"[Task: Message Bots] Selesai ({tasks_done} tugas diselesaikan).")

async def do_visit_sites(client, bot):
    log("[Task: Visit Sites] Memeriksa tugas visit sites...")
    try:
        await client.send_message(bot, "🖥 Visit sites")
        await asyncio.sleep(random.uniform(2.5, 3.5))

        msgs = await client.get_messages(bot, limit=1)
        if msgs and "no new ads available" in msgs[0].text.lower():
            log("[Task: Visit Sites] Tidak ada iklan visit site saat ini.")
            return

        msg = msgs[0]
        site_url = None
        if msg.reply_markup and hasattr(msg.reply_markup, "rows"):
            for row in msg.reply_markup.rows:
                for b in row.buttons:
                    u = getattr(b, "url", None) or getattr(getattr(b, "type", None), "url", None)
                    if u and u.startswith("http"):
                        site_url = u
                        break

        if site_url:
            log(f"[Task: Visit Sites] Mengunjungi URL: {site_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
            }
            try:
                requests.get(site_url, headers=headers, timeout=15)
                log("[Task: Visit Sites] Kunjungan dikirim. Menunggu delay 15 detik...")
                await asyncio.sleep(15)
            except Exception as req_err:
                log(f"[Task: Visit Sites] Peringatan HTTP: {req_err}")

    except Exception as e:
        log(f"[Task: Visit Sites] Error: {e}")

async def run_cycle():
    cfg = load_config()
    log("==================================================")
    log("🚀 Memulai siklus farming TON Click Robot...")
    log("==================================================")

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log("❌ Error: Sesi Telegram tidak terotorisasi. Jalankan setup auth terlebih dahulu.")
        await client.disconnect()
        return False

    try:
        bot = await client.get_entity(cfg.get("bot_username", "TonClickRobot"))

        # 1. Cek saldo awal
        await check_balance(client, bot)
        await asyncio.sleep(2.0)

        # 2. Kerjakan tugas Bot Messaging
        await do_message_bots(client, bot, max_tasks=cfg.get("max_bot_tasks_per_cycle", 5))
        await asyncio.sleep(2.0)

        # 3. Kerjakan tugas Join Chats
        await do_join_chats(client, bot, max_tasks=cfg.get("max_join_tasks_per_cycle", 5))
        await asyncio.sleep(2.0)

        # 4. Kerjakan tugas Visit Sites
        await do_visit_sites(client, bot)
        await asyncio.sleep(2.0)

        # 5. Cek saldo akhir
        final_bal_str = await check_balance(client, bot)

        # 6. Pembersihan channel retensi lama
        if cfg.get("auto_cleanup_old_channels", True):
            await cleanup_retention(client, cfg.get("retention_hours", 72))

        # 7. Auto-Withdraw CryptoBot (0% Fee Instan) bila diaktifkan di config
        if cfg.get("auto_withdraw_cryptobot", True):
            min_thresh = float(cfg.get("min_withdraw_cryptobot_ton", 1.0))
            match = re.search(r"([\d.]+)\s*TON", final_bal_str)
            cur_bal = float(match.group(1)) if match else 0.0
            if cur_bal >= min_thresh:
                log(f"[Auto-WD CryptoBot] Saldo {cur_bal:.7f} TON >= ambang batas {min_thresh:.2f} TON. Memproses penarikan instan ke @CryptoBot...")
                await client.disconnect()
                ok_wd, res_wd = await withdraw_cryptobot()
                log(f"[Auto-WD CryptoBot] Hasil: {res_wd}")
                return True

        # 8. Auto-Withdraw Direct TON (On-Chain) bila saldo >= min_withdraw_ton
        if cfg.get("auto_withdraw_direct", False) and cfg.get("ton_wallet_address"):
            w_addr = cfg.get("ton_wallet_address", "").strip()
            min_thresh = float(cfg.get("min_withdraw_ton", 1.0))
            match = re.search(r"([\d.]+)\s*TON", final_bal_str)
            cur_bal = float(match.group(1)) if match else 0.0
            if w_addr and cur_bal >= min_thresh:
                log(f"[Auto-WD Direct] Saldo {cur_bal:.7f} TON >= ambang batas {min_thresh:.2f} TON. Memproses penarikan ke {w_addr}...")
                await client.disconnect()
                ok_wd, res_wd = await withdraw_direct_ton(w_addr)
                log(f"[Auto-WD Direct] Hasil: {res_wd}")
                return True

        # 8. Auto-Withdraw FaucetPay bila diaktifkan di config
        if cfg.get("auto_withdraw_faucetpay", False) and cfg.get("faucetpay_email"):
            email = cfg.get("faucetpay_email", "").strip()
            match = re.search(r"([\d.]+)\s*TON", final_bal_str)
            cur_bal = float(match.group(1)) if match else 0.0
            if email and cur_bal >= 0.001:
                log(f"[Auto-WD] Saldo {cur_bal:.7f} TON memenuhi syarat FaucetPay. Memproses penarikan...")
                # Putuskan koneksi client loop ini sejenak agar withdraw_faucetpay menggunakan sesi tersendiri
                await client.disconnect()
                ok_wd, res_wd = await withdraw_faucetpay(email)
                log(f"[Auto-WD] Hasil: {res_wd}")
                return True

    except Exception as e:
        log(f"Terjadi kesalahan pada siklus: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()
        log("Siklus selesai. Koneksi ditutup.")

    return True

async def main_loop():
    cfg = load_config()
    interval = cfg.get("cycle_interval_seconds", 900)
    log(f"=== TON Click Robot Auto-Farmer Daemon Dimulai (Interval: {interval}s) ===")

    while True:
        try:
            await run_cycle()
        except Exception as e:
            log(f"Error loop utama: {e}")
        log(f"Menunggu {interval // 60} menit untuk siklus berikutnya...")
        await asyncio.sleep(interval)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            asyncio.run(run_cycle())
        elif sys.argv[1] == "--withdraw" and len(sys.argv) > 2:
            target_email = sys.argv[2]
            target_amt = float(sys.argv[3]) if len(sys.argv) > 3 else None
            ok, msg = asyncio.run(withdraw_faucetpay(target_email, target_amt))
            print(f"STATUS:{'SUCCESS' if ok else 'FAILED'}")
            print(f"MESSAGE:{msg}")
    else:
        asyncio.run(main_loop())
