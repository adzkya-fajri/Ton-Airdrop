#!/usr/bin/env python3
"""
Flux Official (@Fluxofficial_bot) Standalone Auto-Farmer
Mendukung:
- Otentikasi mandiri aman tanpa lock SQLite
- Auto-claim mining siklus 8 jam (/api/claims/mining)
- Klaim daily streak (/api/streak/claim)
- Klaim task sosial aman (/api/tasks/social/confirm & /api/tasks/claim)
- Pelaporan metrik saldo & min swap ke farmers/flux/state.json
- Strictly NO auto-swap
"""

import os
import sys
import time
import json
import uuid
import shutil
import asyncio
import urllib.parse
from datetime import datetime, timezone
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
LOG_FILE = os.path.join(BASE_DIR, "farmer.log")
AUTH_GEN_DIR = os.path.join(os.path.dirname(BASE_DIR), "auth_generator")
TG_SESSION_SRC = os.path.join(AUTH_GEN_DIR, "tg_session.session")
TEMP_SESSION = "/tmp/flux_standalone_session"

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] [FLUX] {msg}"
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
        "bot_username": "Fluxofficial_bot",
        "base_url": "https://fluxx.run.place",
        "cycle_interval_seconds": 1800,
        "auto_claim": True,
        "auto_streak": True,
        "auto_tasks": True,
        "auto_swap": False
    }

def save_state(metrics):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        log(f"Gagal menyimpan state.json: {e}")

def extract_flux_metrics(data):
    """
    Mengekstrak metrik saldo, pending, status mining, dan min swap dari response /api/state
    """
    state = data.get("state", {})
    balance = float(state.get("balance", 0.0))
    pending = float(state.get("pending", 0.0))
    mining = state.get("mining", {})
    market = state.get("market", {})
    withdrawals = state.get("withdrawals", {})

    stops_at = int(mining.get("stopsAt", 0))
    next_claim_at = int(mining.get("nextClaimAt", 0))
    min_swap = int(market.get("minSellFlux", 1000))

    ton_wd_min = 0.5
    if "sources" in withdrawals and "TON" in withdrawals["sources"]:
        ton_wd_min = float(withdrawals["sources"]["TON"].get("minimum", 0.5))

    return {
        "balance": balance,
        "pending": pending,
        "stops_at": stops_at,
        "next_claim_at": next_claim_at,
        "min_swap": min_swap,
        "ton_min_withdraw": ton_wd_min,
        "updated_at": datetime.now().isoformat()
    }

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
        bot = await client.get_input_entity("Fluxofficial_bot")
        res = await client(RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://fluxx.run.place/",
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

class FluxFarmer:
    def __init__(self):
        self.cfg = load_config()
        self.base_url = self.cfg.get("base_url", "https://fluxx.run.place")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": self.cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36")
        })
        self.init_data = self.cfg.get("init_data")

    def authenticate(self):
        """Melakukan login ke endpoint Flux dan memperbarui cookies."""
        if not self.init_data:
            log("init_data kosong, mengambil initData baru dari Telegram...")
            self.init_data = asyncio.run(fetch_fresh_init_data())
            if not self.init_data:
                log("❌ Gagal mendapatkan initData Telegram.")
                return False
            self.cfg["init_data"] = self.init_data
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=2)
            except Exception:
                pass

        try:
            r = self.session.post(
                f"{self.base_url}/api/auth/telegram",
                json={"initData": self.init_data},
                timeout=15
            )
            if r.status_code == 200:
                log("✅ Otentikasi sesi Flux berhasil.")
                return True
            elif r.status_code == 401:
                log("⚠️ Sesi kedaluwarsa (401), memperbarui initData...")
                self.init_data = asyncio.run(fetch_fresh_init_data())
                if self.init_data:
                    self.cfg["init_data"] = self.init_data
                    try:
                        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                            json.dump(self.cfg, f, indent=2)
                    except Exception:
                        pass
                    r2 = self.session.post(f"{self.base_url}/api/auth/telegram", json={"initData": self.init_data}, timeout=15)
                    if r2.status_code == 200:
                        log("✅ Re-otentikasi sesi Flux berhasil.")
                        return True
            log(f"Otentikasi gagal dengan status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            log(f"Error saat otentikasi Flux: {e}")
        return False

    def get_state(self):
        try:
            r = self.session.get(f"{self.base_url}/api/state", timeout=15)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 401:
                if self.authenticate():
                    r = self.session.get(f"{self.base_url}/api/state", timeout=15)
                    if r.status_code == 200:
                        return r.json()
        except Exception as e:
            log(f"Error get_state: {e}")
        return None

    def claim_mining(self):
        try:
            headers = {
                "Content-Type": "application/json",
                "Idempotency-Key": str(uuid.uuid4())
            }
            r = self.session.post(f"{self.base_url}/api/claims/mining", json={}, headers=headers, timeout=15)
            if r.status_code == 200:
                res = r.json()
                amount = res.get("amount", 0)
                log(f"🎉 [KLAIM MINING] Sukses! Mendapatkan {amount} FLX")
                return True
            else:
                log(f"Klaim mining ditolak: {r.status_code} - {r.text[:200]}")
        except Exception as e:
            log(f"Error claim_mining: {e}")
        return False

    def claim_streak(self):
        try:
            headers = {
                "Content-Type": "application/json",
                "Idempotency-Key": str(uuid.uuid4())
            }
            # Coba klaim streak hari ini (1..7)
            for day in range(1, 8):
                r = self.session.post(f"{self.base_url}/api/streak/claim", json={"day": day}, headers=headers, timeout=15)
                if r.status_code == 200:
                    res = r.json()
                    log(f"🎁 [DAILY STREAK] Sukses klaim hari ke-{day}! Reward: {res.get('amount', 0)} FLX")
                    return True
        except Exception as e:
            log(f"Error claim_streak: {e}")
        return False

    def process_social_tasks(self, tasks_data):
        if not tasks_data:
            return
        items = tasks_data.items() if isinstance(tasks_data, dict) else enumerate(tasks_data)
        for key, val in items:
            tid = key if isinstance(tasks_data, dict) else (val.get("id") or val.get("taskId") if isinstance(val, dict) else str(val))
            tinfo = val if isinstance(val, dict) else {}
            claimed = tinfo.get("claimed", False)
            if not claimed and tid:
                try:
                    headers = {"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())}
                    if tid == "telegram":
                        self.session.post(f"{self.base_url}/api/tasks/verify", json={"taskId": "telegram"}, headers=headers, timeout=15)
                    self.session.post(f"{self.base_url}/api/tasks/social/confirm", json={"taskId": tid, "confirmed": True}, headers=headers, timeout=15)
                    r_claim = self.session.post(f"{self.base_url}/api/tasks/claim", json={"taskId": tid}, headers=headers, timeout=15)
                    if r_claim.status_code == 200:
                        res = r_claim.json()
                        reward = res.get("amount", tinfo.get("reward", 0))
                        log(f"✅ [TASK] Berhasil menyelesaikan & klaim task '{tid}'! Reward: +{reward} FLX")
                except Exception as e:
                    log(f"Error proses task {tid}: {e}")

    def run_cycle(self):
        log("--- Memulai Siklus Pemeriksaan Flux ---")
        state_data = self.get_state()
        if not state_data:
            if not self.authenticate():
                log("Gagal otentikasi pada awal siklus.")
                return
            state_data = self.get_state()
            if not state_data:
                log("State data tetap tidak dapat diambil.")
                return

        metrics = extract_flux_metrics(state_data)
        save_state(metrics)
        log(f"📊 [Status Saldo] Saldo: {metrics['balance']:.2f} FLX | Pending: {metrics['pending']:.4f} FLX | Min Swap: {metrics['min_swap']} FLX")

        now_ms = int(time.time() * 1000)
        stops_at = metrics["stops_at"]
        next_claim_at = metrics["next_claim_at"]

        # Cek klaim mining (jika pending > 0 dan waktu klaim telah tiba)
        if self.cfg.get("auto_claim", True):
            if metrics["pending"] > 0 and (now_ms >= next_claim_at or (stops_at > 0 and now_ms >= stops_at)):
                log("Menjalankan klaim mining berkala...")
                if self.claim_mining():
                    # Refresh state setelah klaim
                    refreshed = self.get_state()
                    if refreshed:
                        metrics = extract_flux_metrics(refreshed)
                        save_state(metrics)
            else:
                sisa_seconds = max(0, int((next_claim_at - now_ms) / 1000)) if next_claim_at > now_ms else 0
                log(f"Mining aktif. Sisa waktu sebelum klaim berikutnya: ~{sisa_seconds // 60} minutes.")

        # Cek klaim daily streak
        if self.cfg.get("auto_streak", True):
            self.claim_streak()

        # Cek task
        if self.cfg.get("auto_tasks", True):
            tasks = state_data.get("state", {}).get("tasks", [])
            self.process_social_tasks(tasks)

def main():
    log("=== Daemon Standalone Flux Farmer Diinisialisasi ===")
    farmer = FluxFarmer()
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
