#!/usr/bin/env python3
"""
Static Vein 2.0 (@StaticVein_Bot) Standalone Auto-Farmer
Mendukung:
- Otentikasi mandiri aman tanpa lock SQLite via salinan session Telethon
- Auto-harvest mining energi & VEIN (/api/claim)
- Auto-complete beginner guide tutorial (/api/me action: guide)
- Auto-claim reward login harian (/api/daily)
- Auto-claim tasks komunitas & verifikasi channel (/api/tasks check & claim)
- Auto-claim komisi referral kawan (/api/friends/claim)
- Pelaporan metrik saldo & status ke farmers/staticvein/state.json
"""

import os
import sys
import time
import json
import shutil
import asyncio
import urllib.parse
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
AUTH_GEN_DIR = os.path.join(os.path.dirname(BASE_DIR), "auth_generator")
TG_SESSION_SRC = os.path.join(AUTH_GEN_DIR, "tg_session.session")
TEMP_SESSION = "/tmp/staticvein_standalone_session"

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] [STATICVEIN] {msg}"
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
            log(f"Gagal membaca config: {e}")
    return {
        "bot_username": "StaticVein_Bot",
        "base_url": "https://staticvein.ru",
        "cycle_interval_seconds": 1800,
        "auto_claim": True,
        "auto_daily": True,
        "auto_tasks": True,
        "auto_guide": True,
        "auto_friends": True
    }

def save_state(metrics):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        log(f"Gagal menyimpan state.json: {e}")

async def fetch_fresh_init_data():
    """Fetch new initData from Telegram via session copy to prevent locks."""
    if not os.path.exists(TG_SESSION_SRC):
        log("File tg_session.session not found.")
        return None

    try:
        shutil.copy(TG_SESSION_SRC, f"{TEMP_SESSION}.session")
    except Exception as e:
        log(f"Error copying session: {e}")

    from telethon import TelegramClient
    from telethon.tl.functions.messages import RequestWebViewRequest

    client = TelegramClient(TEMP_SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        log("Client Telethon tidak terotorisasi.")
        await client.disconnect()
        return None

    try:
        bot = await client.get_input_entity("StaticVein_Bot")
        res = await client(RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://staticvein.ru/",
            from_bot_menu=True
        ))
        await client.disconnect()
        if "#tgWebAppData=" in res.url:
            raw = res.url.split("#tgWebAppData=")[1].split("&tgWebAppVersion=")[0]
            return urllib.parse.unquote(raw)
    except Exception as e:
        log(f"Error RequestWebViewRequest: {e}")
        if client.is_connected():
            await client.disconnect()
    return None

async def join_telegram_channel(channel_username):
    """Join Telegram channels via Telethon for successful task verification."""
    clean_username = channel_username.lstrip("@").strip()
    if not clean_username:
        return False

    if not os.path.exists(TG_SESSION_SRC):
        return False

    try:
        shutil.copy(TG_SESSION_SRC, f"{TEMP_SESSION}.session")
    except Exception:
        pass

    from telethon import TelegramClient
    from telethon.tl.functions.channels import JoinChannelRequest

    client = TelegramClient(TEMP_SESSION, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        return False

    success = False
    try:
        await client(JoinChannelRequest(clean_username))
        log(f"Bergabung ke channel Telegram @{clean_username} berhasil.")
        success = True
    except Exception as e:
        log(f"Info join channel @{clean_username}: {e}")
    finally:
        await client.disconnect()
    return success

def extract_staticvein_metrics(user_data):
    """Extract balance, hashrate, daily rate, rank, and status metrics."""
    return {
        "balance": float(user_data.get("balance", 0.0)),
        "pending": float(user_data.get("pendingMined", 0.0)),
        "storage_cap": float(user_data.get("storageCap", 6.56)),
        "daily_rate": float(user_data.get("dailyRate", 6.56)),
        "miner_level": int(user_data.get("minerLevel", 1)),
        "grid_level": int(user_data.get("gridLevel", user_data.get("minerLevel", 1))),
        "hashrate": str(user_data.get("hashrate", "0.01 TH/s")),
        "withdraw_min": float(user_data.get("withdrawMin", 15000.0)),
        "rank_title": str(user_data.get("rankTitle", "Stone Digger")),
        "daily_streak": int(user_data.get("dailyStreak", 0)),
        "updated_at": datetime.now().isoformat()
    }

class StaticVeinFarmer:
    def __init__(self):
        self.cfg = load_config()
        self.base_url = self.cfg.get("base_url", "https://staticvein.ru")
        self.session = requests.Session()
        self.init_data = self.cfg.get("init_data")
        self.update_headers()

    def update_headers(self):
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": self.cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
            "Content-Type": "application/json"
        })
        if self.init_data:
            self.session.headers["Authorization"] = f"tma {self.init_data}"

    def authenticate(self):
        """Memastikan initData valid dan melakukan refresh jika expired."""
        if not self.init_data:
            log("init_data kosong, mengambil initData baru dari Telegram...")
            self.init_data = asyncio.run(fetch_fresh_init_data())
            if not self.init_data:
                log("❌ Gagal mendapatkan initData Telegram.")
                return False
            self.cfg["init_data"] = self.init_data
            self.update_headers()
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=2)
            except Exception:
                pass

        try:
            r = self.session.post(
                f"{self.base_url}/api/me",
                json={"initData": self.init_data},
                timeout=15
            )
            if r.status_code == 200:
                log("✅ Otentikasi sesi Static Vein valid.")
                return True
            elif r.status_code == 401:
                log("⚠️ Sesi kedaluwarsa (401), memperbarui initData...")
                self.init_data = asyncio.run(fetch_fresh_init_data())
                if self.init_data:
                    self.cfg["init_data"] = self.init_data
                    self.update_headers()
                    try:
                        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                            json.dump(self.cfg, f, indent=2)
                    except Exception:
                        pass
                    r2 = self.session.post(f"{self.base_url}/api/me", json={"initData": self.init_data}, timeout=15)
                    if r2.status_code == 200:
                        log("✅ Re-otentikasi sesi Static Vein berhasil.")
                        return True
            log(f"Otentikasi gagal dengan status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log(f"Error saat otentikasi Static Vein: {e}")
        return False

    def get_user_info(self):
        try:
            r = self.session.post(f"{self.base_url}/api/me", json={"initData": self.init_data}, timeout=15)
            if r.status_code == 200:
                return r.json().get("user", {})
            elif r.status_code == 401:
                if self.authenticate():
                    r = self.session.post(f"{self.base_url}/api/me", json={"initData": self.init_data}, timeout=15)
                    if r.status_code == 200:
                        return r.json().get("user", {})
        except Exception as e:
            log(f"Error get_user_info: {e}")
        return None

    def complete_guide(self):
        try:
            r = self.session.post(f"{self.base_url}/api/me", json={"initData": self.init_data, "action": "guide"}, timeout=15)
            if r.status_code == 200:
                log("📖 [GUIDE] Tutorial pemula berhasil diselesaikan.")
                return True
        except Exception as e:
            log(f"Error complete_guide: {e}")
        return False

    def claim_mining(self):
        try:
            r = self.session.post(f"{self.base_url}/api/claim", json={"initData": self.init_data}, timeout=15)
            if r.status_code == 200:
                user = r.json().get("user", {})
                bal = user.get("balance", 0)
                log(f"🎉 [KLAIM MINING] Sukses panen VEIN! Saldo sekarang: {bal:.4f} VEIN")
                return True
            else:
                log(f"Klaim mining ditolak ({r.status_code}): {r.text[:200]}")
        except Exception as e:
            log(f"Error claim_mining: {e}")
        return False

    def claim_daily(self):
        try:
            r = self.session.post(f"{self.base_url}/api/daily", json={"initData": self.init_data}, timeout=15)
            if r.status_code == 200:
                user = r.json().get("user", {})
                streak = user.get("dailyStreak", 1)
                log(f"🎁 [DAILY STREAK] Sukses klaim reward harian! Streak hari ke-{streak}")
                return True
        except Exception as e:
            log(f"Error claim_daily: {e}")
        return False

    def claim_friends(self):
        try:
            r = self.session.post(f"{self.base_url}/api/friends/claim", json={"initData": self.init_data}, timeout=15)
            if r.status_code == 200:
                log("👥 [REFERRAL] Bonus referral berhasil diklaim.")
                return True
        except Exception as e:
            log(f"Error claim_friends: {e}")
        return False

    def process_tasks(self):
        claimed_any = False
        try:
            r = self.session.post(f"{self.base_url}/api/tasks", json={"initData": self.init_data, "action": "list"}, timeout=15)
            if r.status_code != 200:
                return False
            tasks = r.json().get("tasks", [])
            for t in tasks:
                tid = t.get("id")
                claimed = t.get("claimed", False)
                if not claimed and tid:
                    title = t.get("title", tid)
                    channel_url = t.get("url", "")
                    if t.get("checkSub") and channel_url:
                        clean_ch = channel_url.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "").strip("@ ")
                        if clean_ch:
                            asyncio.run(join_telegram_channel(clean_ch))
                    
                    # Verifikasi / check task
                    r_chk = self.session.post(f"{self.base_url}/api/tasks", json={"initData": self.init_data, "action": "check", "taskId": tid}, timeout=15)
                    time.sleep(1.5)
                    # Klaim reward task
                    r_clm = self.session.post(f"{self.base_url}/api/tasks", json={"initData": self.init_data, "action": "claim", "taskId": tid}, timeout=15)
                    if r_clm.status_code == 200:
                        reward = t.get("reward", 0)
                        log(f"✅ [TASK] Sukses verifikasi & klaim task '{title}' (+{reward} VEIN)!")
                        claimed_any = True
                    else:
                        log(f"⚠️ [TASK] Claim failed task '{title}' ({r_clm.status_code}): {r_clm.text[:150]}")
        except Exception as e:
            log(f"Error process_tasks: {e}")
        return claimed_any

    def run_cycle(self):
        log("--- Memulai Siklus Pemeriksaan Static Vein 2.0 ---")
        user = self.get_user_info()
        if not user:
            if not self.authenticate():
                log("Gagal otentikasi pada awal siklus.")
                return
            user = self.get_user_info()
            if not user:
                log("Data profil tetap tidak dapat diambil.")
                return

        metrics = extract_staticvein_metrics(user)
        save_state(metrics)
        log(f"📊 [Status Saldo] Saldo: {metrics['balance']:.2f} VEIN | Pending: {metrics['pending']:.4f} VEIN | Rate: {metrics['daily_rate']:.2f}/hari | Rank: {metrics['rank_title']}")

        has_claimed = False

        # 1. Tutorial Guide
        if self.cfg.get("auto_guide", True) and not user.get("guideSeen", True):
            if self.complete_guide():
                has_claimed = True

        # 2. Daily Reward Claim
        if self.cfg.get("auto_daily", True) and user.get("canClaimDaily", False):
            if self.claim_daily():
                has_claimed = True

        # 3. Mining Claim jika pending > 0.05 atau storage mendekati penuh
        if self.cfg.get("auto_claim", True):
            pending = metrics["pending"]
            cap = metrics["storage_cap"]
            if pending >= 0.05 or (cap > 0 and pending >= cap * 0.8):
                log("Menjalankan klaim hasil penambangan VEIN...")
                if self.claim_mining():
                    has_claimed = True
            else:
                log(f"Penambangan berjalan normal. Akumulasi pending: {pending:.4f}/{cap:.2f} VEIN.")

        # 4. Tasks Claim
        if self.cfg.get("auto_tasks", True):
            if self.process_tasks():
                has_claimed = True

        # 5. Referral Claim
        if self.cfg.get("auto_friends", True) and user.get("referralPending", 0) > 0:
            if self.claim_friends():
                has_claimed = True

        # Refresh profil & simpan state final jika ada klaim yang sukses
        if has_claimed:
            refreshed = self.get_user_info()
            if refreshed:
                metrics = extract_staticvein_metrics(refreshed)
                save_state(metrics)

def main():
    log("=== Daemon Standalone Static Vein Farmer Diinisialisasi ===")
    farmer = StaticVeinFarmer()
    if "--once" in sys.argv:
        farmer.run_cycle()
        return

    interval = farmer.cfg.get("cycle_interval_seconds", 1800)
    while True:
        try:
            farmer.run_cycle()
        except Exception as e:
            log(f"Exception di loop utama: {e}")
        log(f"Waiting for {interval} seconds hingga siklus berikutnya...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
