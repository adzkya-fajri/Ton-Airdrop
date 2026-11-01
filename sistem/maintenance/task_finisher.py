#!/usr/bin/env python3
"""
task_finisher.py - Pembersih & Pelaksana Tugas Tertunda (Task Auto-Finisher)
Menyapu bersih dan mengklaim reward dari tugas-tugas pending di seluruh bot:
1. Raccoon Rush (@RACCOONRUSHapp) - 16 Sponsor Tasks + Missions + Auto Join Channel
2. Thunder Waves (@ThunderWavesBot) - Social & Partner Tasks
3. SoftUSDT & MiniEmpire Apps (Chicken, MinerXRealm, GoldKeepers, EdgeOfEmpire, Gram24)
4. AICMiner (@Aicminer_bot)
"""

import os
import sys
import time
import json
import asyncio
import requests
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(BASE_DIR, "auth_generator", "tg_session")
REPORT_FILE = os.path.join(BASE_DIR, "maintenance", "task_finisher_report.json")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

# ==================== TELETHON HELPER ====================

async def ensure_joined(client, channel_username_or_link):
    """Help user account join Telegram task channels to validate bot verification."""
    try:
        url = channel_username_or_link.strip()
        if "+" in url:
            code = url.split("+")[-1].split("?")[0].split("/")[0]
            await client(ImportChatInviteRequest(code))
            log(f"   ↳ [Telethon] Sukses bergabung ke private channel invite: {code}")
            return True
        elif "joinchat/" in url:
            code = url.split("joinchat/")[-1].split("?")[0].split("/")[0]
            await client(ImportChatInviteRequest(code))
            log(f"   ↳ [Telethon] Sukses bergabung ke private invite: {code}")
            return True
        else:
            raw = url.split("/")[-1].replace("@", "").split("?")[0]
            if not raw:
                return False
            entity = await client.get_input_entity(raw)
            await client(JoinChannelRequest(entity))
            log(f"   ↳ [Telethon] Sukses bergabung ke @{raw}")
            return True
    except Exception as e:
        # User mungkin sudah bergabung sebelumnya atau link expired
        return False

# ==================== RACCOON RUSH TASK FINISHER ====================

async def finish_raccoon_rush(client):
    log("==================================================")
    log("🦝 [Task Finisher] Memeriksa Tugas Raccoon Rush...")
    log("==================================================")
    cfg_path = os.path.join(BASE_DIR, "raccoonrush", "config.json")
    if not os.path.exists(cfg_path):
        log("❌ config.json Raccoon Rush not found.")
        return {"bot": "RaccoonRush", "success": 0, "failed": 0, "reward": 0}

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    url = cfg.get("api_url", "https://qcxtajojlkqhgesbciwx.supabase.co/functions/v1/rr-api")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"
    }

    def api_call(action, data=None):
        body = {
            "action": action,
            "initData": cfg.get("init_data", ""),
            "deviceId": cfg.get("device_id", ""),
            "ref": ""
        }
        if data:
            body.update(data)
        try:
            r = requests.post(url, json=body, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            log(f"   ⚠️ API Error: {e}")
        return None

    init_res = api_call("init")
    if not init_res or not init_res.get("ok"):
        log("❌ Gagal inisialisasi API Raccoon Rush.")
        return {"bot": "RaccoonRush", "success": 0, "failed": 0, "reward": 0}

    st = init_res.get("state", {})
    user = st.get("user", {})
    done_missions = user.get("done", {})
    ctasks = st.get("ctasks", [])
    
    total_claimed = 0
    total_rp = 0

    # 1. Kerjakan Community / Sponsor Tasks (ctasks)
    for t in ctasks:
        tid = t.get("id")
        title = t.get("title", f"Task #{tid}")
        t_url = t.get("url", "")
        kind = t.get("kind", "link")
        wait_sec = t.get("wait", 10)
        rew = t.get("reward", 25)

        if t.get("done"):
            continue

        log(f"📋 Memproses Raccoon Task #{tid}: '{title}' ({kind})...")

        # Jika tugas berupa channel Telegram, gabung via Telethon
        if kind == "channel" and "t.me/" in t_url:
            await ensure_joined(client, t_url)
            await asyncio.sleep(1.0)

        # Start task
        if not t.get("started"):
            r_start = api_call("ctask_start", {"id": tid})
            if r_start and r_start.get("ok"):
                log(f"   ⏳ Timer tugas dimulai, menunggu {wait_sec + 2} seconds...")
                await asyncio.sleep(wait_sec + 2)
            else:
                log(f"   ⚠️ Gagal memulai task #{tid}")
                continue
        else:
            await asyncio.sleep(wait_sec)

        # Claim task
        r_claim = api_call("ctask_claim", {"id": tid})
        if r_claim and r_claim.get("ok"):
            log(f"   🎉 SUKSES KLAIM #{tid} '{title}': +{rew} RP!")
            total_claimed += 1
            total_rp += rew
        else:
            err = r_claim.get("error") if r_claim else "No response"
            log(f"   ⚠️ Klaim #{tid} tertunda/gagal: {err}")

        await asyncio.sleep(1.5)

    # 2. Periksa & Klaim Base Missions (Missions combo)
    if not done_missions.get("missions"):
        # Hitung berapa misi yang sudah selesai
        # jika 4 misi selesai, klaim bonus 150 RP
        r_miss = api_call("claim", {"task": "missions"})
        if r_miss and r_miss.get("ok"):
            log(f"🎉 SUKSES KLAIM Bonus Combo 'Finish 4 Missions': +{r_miss.get('reward', 150)} RP!")
            total_claimed += 1
            total_rp += r_miss.get("reward", 150)

    # 3. Status akhir
    final_init = api_call("init")
    final_pts = final_init.get("state", {}).get("user", {}).get("points", 0) if final_init else "N/A"
    final_lvl = final_init.get("state", {}).get("user", {}).get("level", 1) if final_init else "N/A"
    log(f"🦝 Raccoon Rush Selesai: +{total_claimed} Task (+{total_rp} RP) | Saldo Baru: {final_pts:,} RP (Level {final_lvl})")

    return {
        "bot": "RaccoonRush",
        "success": total_claimed,
        "reward_rp": total_rp,
        "final_balance": final_pts,
        "level": final_lvl
    }

# ==================== THUNDER WAVES TASK FINISHER ====================

async def finish_thunderwaves(client):
    log("==================================================")
    log("🌊 [Task Finisher] Memeriksa Tugas Thunder Waves...")
    log("==================================================")
    cfg_path = os.path.join(BASE_DIR, "thunderwaves", "config.json")
    if not os.path.exists(cfg_path):
        return {"bot": "ThunderWaves", "success": 0, "reward": 0}

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    init_data = cfg.get("init_data", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"tma {init_data}",
        "Origin": "https://thunderwaves.site",
        "Referer": "https://thunderwaves.site/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36"
    }

    claimed_count = 0
    total_waves = 0

    try:
        r = requests.get("https://api.thunderwaves.site/api/tasks", headers=headers, timeout=15)
        if r.status_code == 200:
            tasks_data = r.json()
            tasks = tasks_data.get("tasks", []) if isinstance(tasks_data, dict) else tasks_data
            log(f"📋 Ditemukan {len(tasks)} tugas di Thunder Waves.")

            for t in tasks:
                tid = t.get("id")
                title = t.get("title", f"Task #{tid}")
                reward = t.get("reward", 0)
                status = t.get("status", "")
                t_url = t.get("url") or ""
                category = t.get("category", "")

                if status in ["claimed", "completed"]:
                    continue

                # Lewati tugas tayangan iklan SDK (Adsgram, Monetag, dsb)
                if any(ad in title.lower() for ad in ["adsgram", "monetag", "gigapub", "adeixum", "usl ads"]):
                    continue

                log(f"🌊 Memproses Thunder Task #{tid}: '{title}' ({category}) Status: {status}...")

                if "t.me/" in t_url:
                    await ensure_joined(client, t_url)
                    await asyncio.sleep(1.5)

                if status != "started":
                    # Start task
                    try:
                        r_st = requests.post(f"https://api.thunderwaves.site/api/tasks/{tid}/start", headers=headers, json={}, timeout=15)
                        log(f"   ⏳ Start task status: {r_st.status_code}")
                        await asyncio.sleep(3.0)
                    except Exception as se:
                        log(f"   ⚠️ Start error: {se}")

                # Claim task
                try:
                    r_cl = requests.post(f"https://api.thunderwaves.site/api/tasks/{tid}/claim", headers=headers, json={}, timeout=15)
                    if r_cl.status_code == 200:
                        res_json = r_cl.json()
                        rew = res_json.get("reward", reward)
                        log(f"   🎉 SUKSES KLAIM '{title}': +{rew} Waves!")
                        claimed_count += 1
                        total_waves += rew
                    else:
                        log(f"   ⚠️ Claim respon: {r_cl.status_code} {r_cl.text[:80]}")
                except Exception as ce:
                    log(f"   ⚠️ Claim error: {ce}")

                await asyncio.sleep(1.5)
    except Exception as e:
        log(f"⚠️ Error Thunder Waves tasks: {e}")

    # Cek saldo terkini
    try:
        r_me = requests.get("https://api.thunderwaves.site/api/me", headers=headers, timeout=10)
        curr_bal = r_me.json().get("balance", "N/A") if r_me.status_code == 200 else "N/A"
    except Exception:
        curr_bal = "N/A"

    log(f"🌊 Thunder Waves Selesai: +{claimed_count} Task (+{total_waves} Waves) | Saldo: {curr_bal} Waves")
    return {"bot": "ThunderWaves", "success": claimed_count, "reward_waves": total_waves, "balance": curr_bal}

# ==================== SOFTUSDT / MINIEMPIRE TASK FINISHER ====================

async def finish_miniempire(client):
    log("==================================================")
    log("💵 [Task Finisher] Memeriksa Tugas MiniEmpire (SoftUSDT, dll)...")
    log("==================================================")
    import urllib.parse
    
    tenants = [
        {"name": "SoftUSDT", "dir": "softusdt", "tid": 2015},
        {"name": "GoldKeepers", "dir": "goldkeepers", "tid": 1406},
        {"name": "ChickenEmpire", "dir": "chickenempire", "tid": 1523},
        {"name": "GRAM24", "dir": "gram24", "tid": 2176}
    ]

    total_claims = 0
    results_detail = []

    for t_info in tenants:
        t_name = t_info["name"]
        tid = t_info["tid"]
        cfg_path = os.path.join(BASE_DIR, t_info["dir"], "config.json")
        if not os.path.exists(cfg_path):
            continue

        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        init_data = cfg.get("init_data", "")
        if not init_data:
            continue

        headers = {
            "Origin": "https://app.miniempire.app",
            "Referer": f"https://app.miniempire.app/miniapp/index.html?tid={tid}&lang=en",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }

        try:
            r = requests.get(
                f"https://app.miniempire.app/miniapp/tasks?tid={tid}&initData={urllib.parse.quote(init_data)}",
                headers=headers,
                timeout=12
            )
            if r.status_code == 200:
                tasks = r.json().get("tasks", [])
                bot_claims = 0
                for t in tasks:
                    if not t.get("completed"):
                        t_id = t.get("id")
                        label = str(t.get("labelEn") or t_id)
                        target = t.get("target") or ""

                        # Lewati tugas referral berjenjang
                        if "invite" in label.lower() or "referral" in label.lower():
                            continue

                        log(f"   📋 [{t_name}] Memproses Task: '{label}'...")
                        if "t.me/" in target:
                            await ensure_joined(client, target)
                            await asyncio.sleep(1.0)

                        # Start
                        try:
                            requests.post(
                                f"https://app.miniempire.app/miniapp/tasks/start?tid={tid}",
                                json={"initData": init_data, "task_id": t_id},
                                headers=headers,
                                timeout=10
                            )
                            await asyncio.sleep(1.5)
                        except Exception:
                            pass

                        # Claim
                        claim_payload = {"initData": init_data, "task_id": t_id}
                        if target:
                            claim_payload["referral_link"] = target
                        try:
                            rc = requests.post(
                                f"https://app.miniempire.app/miniapp/tasks/claim?tid={tid}",
                                json=claim_payload,
                                headers=headers,
                                timeout=10
                            )
                            if rc.status_code == 200 and rc.json().get("ok"):
                                pips = rc.json().get("pips_awarded", t.get("pips", 0))
                                log(f"      🎉 Sukses klaim '{label}': +{pips} Pips!")
                                bot_claims += 1
                                total_claims += 1
                        except Exception as ce:
                            log(f"      ⚠️ Claim error: {ce}")

                results_detail.append({"tenant": t_name, "claimed": bot_claims})
        except Exception as e:
            log(f"   ⚠️ [{t_name}] Gagal memeriksa tugas: {e}")

    log(f"💵 MiniEmpire Selesai: Total {total_claims} task berhasil diselesaikan.")
    return {"bot": "MiniEmpire", "success": total_claims, "details": results_detail}

# ==================== MAIN EXECUTION ====================

async def main():
    print("=" * 70)
    print("🧹 PEMBERSIH TUGAS TERTUNDA (TASK AUTO-FINISHER)")
    print("Menyapu bersih tugas sosial, sponsor & channel di seluruh bot...")
    print("=" * 70)

    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Sesi Telegram tidak terotorisasi. Jalankan login terlebih dahulu.")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"👤 Otorisasi Telegram: {me.first_name} (@{me.username}) ID: {me.id}\n")

    results = []

    # 1. Raccoon Rush
    try:
        r1 = await finish_raccoon_rush(client)
        results.append(r1)
    except Exception as e:
        log(f"❌ Exception Raccoon Rush: {e}")

    # 2. Thunder Waves
    try:
        r2 = await finish_thunderwaves(client)
        results.append(r2)
    except Exception as e:
        log(f"❌ Exception Thunder Waves: {e}")

    # 3. SoftUSDT & MiniEmpire Tenants
    try:
        r3 = await finish_miniempire(client)
        results.append(r3)
    except Exception as e:
        log(f"❌ Exception MiniEmpire: {e}")

    await client.disconnect()

    # Simpan ringkasan laporan
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    }
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 70)
    print("🎉 SEMUA PEMERIKSAAN & PEMBERSIHAN TUGAS SELESAI!")
    print(f"📄 Laporan tersimpan di: {REPORT_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
