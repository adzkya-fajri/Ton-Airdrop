#!/usr/bin/env python3
"""
ClickBee Multi-Crypto Network Auto-Farmer Daemon
Automates Micro-Task & PTC (Paid-To-Click) tasks across:
1. @ClickBeeLTCBot (Litecoin - LTC)
2. @ClickBeeBot (Tron - TRX)
3. @ClickBeeDOGEBot (Dogecoin - DOGE)

Supported Tasks:
- 📢 Join Channels (Join sponsor channels/groups & record retention)
- 🤖 Join Bots (Start sponsor bots & forward verification message)
- 💻 Visit Sites (HTTP PTC visit with simulated browser agent)
- 💰 Balance Tracking & Channel Retention Cleanup
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
SESSION_FILE = os.path.join(BASE_DIR, "clickbee_session")

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
        "bots": [
            {"username": "ClickBeeLTCBot", "coin": "LTC", "min_withdraw": 0.003},
            {"username": "ClickBeeBot", "coin": "TRX", "min_withdraw": 3.0},
            {"username": "ClickBeeDOGEBot", "coin": "DOGE", "min_withdraw": 3.0}
        ],
        "cycle_interval_seconds": 900,
        "max_join_tasks_per_cycle": 5,
        "max_bot_tasks_per_cycle": 5,
        "max_visit_tasks_per_cycle": 5,
        "retention_hours": 48,
        "auto_cleanup_old_channels": True
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
                log(f"[Retention] Channel/Target '{ch_ident}' melewati masa retensi {retention_hours}h. Meninggalkan...")
                try:
                    if str(ch_ident).isdigit():
                        entity = await client.get_entity(int(ch_ident))
                    else:
                        entity = await client.get_entity(ch_ident)
                    await client(functions.channels.LeaveChannelRequest(entity))
                    log(f"[Retention] Berhasil meninggalkan '{ch_ident}'.")
                except Exception as ex:
                    log(f"[Retention] Info saat meninggalkan '{ch_ident}': {ex}")
                to_delete.append(ch_ident)
                await asyncio.sleep(random.uniform(4.0, 7.0))
        except Exception as e:
            log(f"[Retention] Error evaluasi '{ch_ident}': {e}")

    if to_delete:
        for k in to_delete:
            retention.pop(k, None)
        save_retention(retention)

async def check_balance(client, bot_entity, coin_name):
    try:
        await client.send_message(bot_entity, "💰 Balance")
        await asyncio.sleep(2.0)
        msgs = await client.get_messages(bot_entity, limit=3)
        for m in msgs:
            if m.sender_id == bot_entity.id and ("balance" in m.text.lower() or "account details" in m.text.lower()):
                bal_clean = " ".join([l.strip() for l in m.text.splitlines() if l.strip()])
                log(f"[{coin_name} Balance] {bal_clean}")
                return m.text.strip()
    except Exception as e:
        log(f"[{coin_name} Balance] Gagal memeriksa saldo: {e}")
    return ""

async def reset_menu(client, bot_entity):
    """Mengirim pesan 🔙 Back jika bot tersangkut di sub-prompt."""
    try:
        msgs = await client.get_messages(bot_entity, limit=1)
        if msgs and msgs[0].reply_markup and hasattr(msgs[0].reply_markup, "rows"):
            for row in msgs[0].reply_markup.rows:
                for b in row.buttons:
                    if "back" in b.text.lower():
                        await client.send_message(bot_entity, b.text)
                        await asyncio.sleep(1.5)
                        return
    except Exception:
        pass

async def do_join_channels(client, bot_entity, bot_info, max_tasks=5):
    coin = bot_info.get("coin", "COIN")
    log(f"[{coin}: Join Channels] Memeriksa tugas gabung channel...")
    tasks_done = 0
    retention = load_retention()

    while tasks_done < max_tasks:
        try:
            await client.send_message(bot_entity, "📢 Join Channels")
            await asyncio.sleep(random.uniform(2.5, 3.5))

            msgs = await client.get_messages(bot_entity, limit=1)
            if not msgs:
                break
            msg = msgs[0]

            if any(w in msg.text.lower() for w in ["no new ads", "no ads available", "try again later"]):
                log(f"[{coin}: Join Channels] Tidak ada tugas channel baru.")
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
                        if "joined" in b.text.lower():
                            joined_btn = b
                        if "skip" in b.text.lower():
                            skip_btn = b

            if not channel_url:
                urls = re.findall(r"https?://(?:t\.me|telegram\.me)/[^\s\)\"]+", msg.text)
                if urls:
                    channel_url = urls[0]

            if not channel_url or not joined_btn:
                if "forward a message" in msg.text.lower():
                    await reset_menu(client, bot_entity)
                break

            log(f"[{coin}: Join Channels] Menargetkan channel: {channel_url}")
            ch_clean = channel_url.split("?")[0].replace("https://t.me/", "").replace("https://telegram.me/", "").replace("@", "").strip("/")

            joined_ok = False
            saved_key = channel_url
            try:
                if ch_clean.startswith("+") or "joinchat" in channel_url:
                    invite_hash = channel_url.split("+")[-1].split("joinchat/")[-1]
                    res = await asyncio.wait_for(client(functions.messages.ImportChatInviteRequest(invite_hash)), timeout=12.0)
                    joined_ok = True
                    saved_key = channel_url
                else:
                    target_entity = await asyncio.wait_for(client.get_entity(ch_clean), timeout=12.0)
                    await asyncio.wait_for(client(functions.channels.JoinChannelRequest(target_entity)), timeout=12.0)
                    joined_ok = True
                    saved_key = str(getattr(target_entity, "id", None) or getattr(target_entity, "username", None) or channel_url)
            except errors.UserAlreadyParticipantError:
                joined_ok = True
            except Exception as join_err:
                log(f"[{coin}: Join Channels] Error join ({channel_url}): {join_err}")
                if skip_btn:
                    try:
                        await msg.click(text=skip_btn.text)
                        await asyncio.sleep(2.0)
                    except Exception:
                        pass
                break

            if joined_ok:
                await asyncio.sleep(random.uniform(2.0, 3.5))
                try:
                    await msg.click(text=joined_btn.text)
                except Exception:
                    data_val = getattr(getattr(joined_btn, "type", None), "data", None)
                    if data_val:
                        await msg.click(data=data_val)

                await asyncio.sleep(random.uniform(2.5, 4.0))
                res_msgs = await client.get_messages(bot_entity, limit=2)
                reward_found = False
                for r in reversed(res_msgs):
                    if any(w in r.text.lower() for w in ["earned", "congratulations", "success"]):
                        log(f"[{coin}: Join Channels] 🎉 Reward: {r.text.strip()}")
                        tasks_done += 1
                        reward_found = True
                        retention[str(saved_key)] = datetime.now().isoformat()
                        save_retention(retention)
                        break

                if not reward_found and skip_btn:
                    try:
                        await msg.click(text=skip_btn.text)
                    except Exception:
                        pass

            await asyncio.sleep(random.uniform(3.0, 5.0))

        except Exception as e:
            log(f"[{coin}: Join Channels] Kesalahan: {e}")
            break

    log(f"[{coin}: Join Channels] Selesai ({tasks_done} tugas).")

async def do_join_bots(client, bot_entity, bot_info, max_tasks=5):
    coin = bot_info.get("coin", "COIN")
    log(f"[{coin}: Join Bots] Memeriksa tugas bot...")
    tasks_done = 0

    while tasks_done < max_tasks:
        try:
            await client.send_message(bot_entity, "🤖 Join Bots")
            await asyncio.sleep(random.uniform(2.5, 3.5))

            msgs = await client.get_messages(bot_entity, limit=1)
            if not msgs:
                break
            msg = msgs[0]

            if any(w in msg.text.lower() for w in ["no new ads", "no ads available", "try again later"]):
                log(f"[{coin}: Join Bots] Tidak ada tugas bot baru.")
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
                urls = re.findall(r"https?://(?:t\.me|telegram\.me)/[^\s\)\"]+", msg.text)
                if urls:
                    bot_url = urls[0]

            if not bot_url:
                log(f"[{coin}: Join Bots] Link bot tidak ditemukan. Reset menu.")
                await reset_menu(client, bot_entity)
                break

            parsed = urllib.parse.urlparse(bot_url)
            target_username = parsed.path.strip("/").split("/")[0]
            start_param = urllib.parse.parse_qs(parsed.query).get("start", [None])[0]

            log(f"[{coin}: Join Bots] Menghubungi target @{target_username} (start: {start_param})")
            target_entity = await client.get_entity(target_username)

            if start_param:
                await client.send_message(target_entity, f"/start {start_param}")
            else:
                await client.send_message(target_entity, "/start")

            await asyncio.sleep(random.uniform(2.5, 4.0))

            reply_msgs = await client.get_messages(target_entity, limit=1)
            if not reply_msgs:
                log(f"[{coin}: Join Bots] Bot @{target_username} tidak membalas. Lewati.")
                if skip_btn:
                    try:
                        await msg.click(text=skip_btn.text)
                    except Exception:
                        pass
                await reset_menu(client, bot_entity)
                continue

            target_reply = reply_msgs[0]
            log(f"[{coin}: Join Bots] Mem-forward balasan ke @{bot_info['username']}...")
            try:
                await client.forward_messages(bot_entity, target_reply)
            except errors.ChatForwardsRestrictedError:
                log(f"[{coin}: Join Bots] Target bot memiliki batasan protected content. Melewati...")
                if skip_btn:
                    try:
                        await msg.click(text=skip_btn.text)
                        await asyncio.sleep(2.0)
                    except Exception:
                        pass
                await reset_menu(client, bot_entity)
                continue
            except Exception as fwd_err:
                log(f"[{coin}: Join Bots] Gagal forward: {fwd_err}")
                if skip_btn:
                    try:
                        await msg.click(text=skip_btn.text)
                    except Exception:
                        pass
                await reset_menu(client, bot_entity)
                continue

            await asyncio.sleep(random.uniform(2.5, 4.0))
            confirm_msgs = await client.get_messages(bot_entity, limit=2)
            for cm in reversed(confirm_msgs):
                if any(w in cm.text.lower() for w in ["earned", "congratulations", "success"]):
                    log(f"[{coin}: Join Bots] 🎉 Reward: {cm.text.strip()}")
                    tasks_done += 1
                    break

            await asyncio.sleep(random.uniform(3.0, 5.0))

        except Exception as e:
            log(f"[{coin}: Join Bots] Kesalahan: {e}")
            await reset_menu(client, bot_entity)
            break

    log(f"[{coin}: Join Bots] Selesai ({tasks_done} tugas).")

async def do_visit_sites(client, bot_entity, bot_info, max_tasks=5):
    coin = bot_info.get("coin", "COIN")
    log(f"[{coin}: Visit Sites] Memeriksa tugas visit sites...")
    tasks_done = 0

    while tasks_done < max_tasks:
        try:
            await client.send_message(bot_entity, "💻 Visit Sites")
            await asyncio.sleep(random.uniform(2.5, 3.5))

            msgs = await client.get_messages(bot_entity, limit=1)
            if not msgs:
                break
            msg = msgs[0]

            if any(w in msg.text.lower() for w in ["no new ads", "no ads available", "try again later"]):
                log(f"[{coin}: Visit Sites] Tidak ada iklan visit sites.")
                break

            site_url = None
            skip_btn = None

            if msg.reply_markup and hasattr(msg.reply_markup, "rows"):
                for row in msg.reply_markup.rows:
                    for b in row.buttons:
                        u = getattr(b, "url", None) or getattr(getattr(b, "type", None), "url", None)
                        if u and u.startswith("http"):
                            site_url = u
                        if "skip" in b.text.lower():
                            skip_btn = b

            if not site_url:
                urls = re.findall(r"https?://[^\s\)\"]+", msg.text)
                if urls:
                    site_url = urls[0]

            if not site_url:
                log(f"[{coin}: Visit Sites] URL tidak ditemukan. Selesai.")
                break

            log(f"[{coin}: Visit Sites] Mengunjungi URL: {site_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
            }
            try:
                await asyncio.to_thread(requests.get, site_url, headers=headers, timeout=10)
                log(f"[{coin}: Visit Sites] Kunjungan dikirim. Menunggu countdown 15 detik...")
                await asyncio.sleep(15)
                tasks_done += 1
            except Exception as req_err:
                log(f"[{coin}: Visit Sites] HTTP notice: {req_err}")
                if skip_btn:
                    try:
                        await msg.click(text=skip_btn.text)
                    except Exception:
                        pass
                break

            await asyncio.sleep(random.uniform(2.0, 4.0))

        except Exception as e:
            log(f"[{coin}: Visit Sites] Kesalahan: {e}")
            break

    log(f"[{coin}: Visit Sites] Selesai ({tasks_done} tugas).")

async def run_cycle():
    cfg = load_config()
    bots = cfg.get("bots", [])
    max_join = cfg.get("max_join_tasks_per_cycle", 5)
    max_bot = cfg.get("max_bot_tasks_per_cycle", 5)
    max_visit = cfg.get("max_visit_tasks_per_cycle", 5)

    log("==================================================")
    log("🚀 Memulai siklus farming ClickBee Multi-Crypto...")
    log("==================================================")

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    client.session.set_dc(5, "91.108.56.147", 443)
    await client.connect()

    if not await client.is_user_authorized():
        log("❌ Error: Sesi Telegram tidak terotorisasi.")
        await client.disconnect()
        return False

    try:
        for b_info in bots:
            username = b_info.get("username")
            coin = b_info.get("coin", "COIN")
            log(f"--- [Memproses Bot: @{username} ({coin})] ---")

            try:
                bot_entity = await client.get_entity(username)

                # 1. Reset menu bila tertahan di sub-prompt
                await reset_menu(client, bot_entity)

                # 2. Periksa saldo awal
                await check_balance(client, bot_entity, coin)
                await asyncio.sleep(2.0)

                # 3. Tugas Join Channels
                await do_join_channels(client, bot_entity, b_info, max_tasks=max_join)
                await asyncio.sleep(2.0)

                # 4. Tugas Join Bots
                await do_join_bots(client, bot_entity, b_info, max_tasks=max_bot)
                await asyncio.sleep(2.0)

                # 5. Tugas Visit Sites
                await do_visit_sites(client, bot_entity, b_info, max_tasks=max_visit)
                await asyncio.sleep(2.0)

                # 6. Periksa saldo akhir
                await check_balance(client, bot_entity, coin)
                await asyncio.sleep(2.0)

            except Exception as bot_err:
                log(f"Error saat memproses @{username}: {bot_err}")

        # 7. Pembersihan channel retensi
        if cfg.get("auto_cleanup_old_channels", True):
            await cleanup_retention(client, cfg.get("retention_hours", 48))

    except Exception as e:
        log(f"Terjadi kesalahan pada siklus ClickBee: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()
        log("Siklus ClickBee selesai. Koneksi ditutup.")

    return True

async def main_loop():
    cfg = load_config()
    interval = cfg.get("cycle_interval_seconds", 900)
    log(f"=== ClickBee Multi-Crypto Farmer Daemon Dimulai (Interval: {interval}s) ===")

    while True:
        try:
            await run_cycle()
        except Exception as e:
            log(f"Error loop utama: {e}")
        log(f"Menunggu {interval // 60} menit untuk siklus berikutnya...")
        await asyncio.sleep(interval)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        asyncio.run(run_cycle())
    else:
        asyncio.run(main_loop())
