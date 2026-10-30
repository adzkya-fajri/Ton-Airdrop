#!/usr/bin/env python3
"""
refresh_pass.py - Auto-fetch x-human-pass for Victor's Company using Headless Google Chrome & Nodriver (CDP Stealth)
Flow:
1. Reads tgWebAppData / authorization from config.json
2. Launches headless Google Chrome using nodriver
3. Intercepts /api/auth/login network response via Chrome DevTools Protocol
4. Captures the fresh humanPass and writes it directly to config.json
"""

import os
import sys
import json
import time
import asyncio
import datetime
import nodriver as uc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_PATH = os.path.join(BASE_DIR, "farmer.log")

def log(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] [Auto-Pass] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(formatted + "\n")
            f.flush()
    except Exception:
        pass

async def refresh_human_pass():
    if not os.path.exists(CONFIG_PATH):
        log("config.json tidak ditemukan.")
        return False

    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)

    auth = cfg.get("authorization", "").strip()
    if not auth:
        log("Authorization token kosong di config.json.")
        return False

    # Bersihkan prefix tma jika ada
    tg_data = auth[4:] if auth.startswith("tma ") else auth

    # Bangun URL mini-app Victor
    target_url = f"https://app.victors.company/#tgWebAppData={tg_data}"
    log("Membuka headless Google Chrome untuk menyelesaikan Turnstile...")

    browser = None
    try:
        browser = await uc.start(
            headless=True,
            browser_executable_path="/opt/google/chrome/google-chrome"
        )
        page = browser.main_tab
        await page.send(uc.cdp.network.enable())

        captured_pass = None
        auth_error = None

        async def on_response(event: uc.cdp.network.ResponseReceived):
            nonlocal captured_pass, auth_error
            url = event.response.url
            if "/auth/login" in url or "/auth/reset" in url:
                try:
                    body, is_base64 = await page.send(
                        uc.cdp.network.get_response_body(request_id=event.request_id)
                    )
                    data = json.loads(body)
                    if data.get("humanPass"):
                        captured_pass = data.get("humanPass")
                    elif data.get("code") == "TG_AUTH":
                        auth_error = "TG_AUTH_EXPIRED"
                except Exception as e:
                    pass

        page.add_handler(uc.cdp.network.ResponseReceived, on_response)
        await page.get(target_url)

        # Tunggu hingga Cloudflare Turnstile selesai dan /auth/login terpanggil (maks 25 detik)
        for i in range(25):
            await asyncio.sleep(1)
            if captured_pass:
                break
            if auth_error == "TG_AUTH_EXPIRED":
                log("PERINGATAN: Sesi Telegram (tgWebAppData) telah expired di sisi Telegram. Perlu buka ulang dari Telegram!")
                return False

        if captured_pass:
            cfg["x-human-pass"] = captured_pass
            with open(CONFIG_PATH, "w") as f:
                json.dump(cfg, f, indent=4)
            log(f">> SUKSES! Mendapatkan x-human-pass baru: {captured_pass[:16]}... <<")
            return True
        else:
            log("Timeout: Tidak berhasil menangkap humanPass dalam 25 detik.")
            return False

    except Exception as e:
        log(f"Error saat menjalankan browser: {e}")
        return False
    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                pass
        # Tunggu sebentar agar semua task asyncio yang pending (subprocess transport) selesai
        # sebelum event loop ditutup, mencegah RuntimeError 'Event loop is closed'
        try:
            # Jalankan semua coroutine yang tersisa
            pending = asyncio.all_tasks()
            if pending:
                for task in pending:
                    task.cancel()
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass

def main():
    log("=== Memulai Auto-Refresher Human Pass ===")
    try:
        success = asyncio.run(refresh_human_pass())
    except Exception as e:
        log(f"asyncio.run error: {e}")
        success = False
    # Beri waktu singkat agar subprocess transport ter-cleanup dengan benar
    time.sleep(0.5)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
