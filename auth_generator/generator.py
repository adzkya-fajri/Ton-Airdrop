#!/usr/bin/env python3
"""
Telegram WebApp Auto-Token Generator Daemon (Master Multi-Bot)
Periodically fetches fresh Telegram WebApp authentication signatures (initData)
directly from Telegram servers via MTProto (Telethon) and injects them into
each miner's config.json.

Supported Miners:
1. VYRO Miner ($VYRO)
2. ATF Miner ($ATF)
3. DRAM Miner ($DRAM)
4. MRG Miner ($MRG)
5. Victor's Company ($VIC)
6. Starvey Shop (Telegram Stars)
7. Diggo Miner ($DIGGO)
8. mAInet Miner ($MAI)
9. Epsilon Miner ($EPS)
10. Gram Buddies ($GRAM)
11. ODRA Mining ($ODRA)
"""

import os
import sys
import time
import json
import asyncio
import urllib.parse
from datetime import datetime
import requests
import subprocess
from telethon import TelegramClient, functions, types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
FARMERS_DIR = os.path.join(ROOT_DIR, "farmers")
SESSION_FILE = os.path.join(BASE_DIR, "tg_session")
LOG_FILE = os.path.join(BASE_DIR, "generator.log")

API_ID = 30234133
API_HASH = "142e316c8fce3f9a94b655a3d3593aee"

REFRESH_INTERVAL_SECONDS = 1500  # Refresh every 25 minutes (before VYRO's 60m TTL)

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

def parse_init_data(url):
    parsed = urllib.parse.urlparse(url)
    fragment = urllib.parse.parse_qs(parsed.fragment)
    return fragment.get("tgWebAppData", [""])[0]

async def refresh_vyro(client):
    try:
        log("[VYRO] Mengambil token baru via @vyrodrop_bot...")
        bot = await client.get_entity("vyrodrop_bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://vyro.run.place/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "vyro", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["auth"] = f"tma {init_data}"
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[VYRO] >> SUKSES menyegarkan token VYRO! <<")
            return True
    except Exception as e:
        log(f"[VYRO] Error: {e}")
    return False

async def refresh_atf(client):
    try:
        log("[ATF] Mengambil token baru via @ATF_AIRDROP_bot...")
        bot = await client.get_entity("ATF_AIRDROP_bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://atfminers.asloni.online/miner/index.html?entry=energy_full",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        t = int(time.time() * 1000)
        login_url = f"https://atfminers.asloni.online/miner/index.php?action=login&t={t}"
        headers = {
            "Origin": "https://atfminers.asloni.online",
            "Referer": "https://atfminers.asloni.online/miner/index.html",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
            "Content-Type": "application/json"
        }
        r = requests.post(login_url, headers=headers, json={"initData": init_data}, timeout=15)
        cookies = r.cookies.get_dict()
        tma_session = cookies.get("atf_tma_session", "")

        cfg_path = os.path.join(FARMERS_DIR, "atf", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            if tma_session:
                cfg["tma_session"] = tma_session
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[ATF] >> SUKSES menyegarkan session & initData ATF! <<")
            return True
    except Exception as e:
        log(f"[ATF] Error: {e}")
    return False

async def refresh_dram(client):
    try:
        log("[DRAM] Mengambil token baru via @dramminerbot...")
        bot = await client.get_entity("dramminerbot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://dram.faithton.online/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "dram", "config.json")
        with open(cfg_path, "r") as f:
            cfg = json.load(f)

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://dram.faithton.online",
            "Referer": "https://dram.faithton.online/",
            "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
        }
        device = cfg.get("device", {})
        payload = {"initData": init_data, "device": device}
        r = requests.post("https://dram.faithton.online/api/auth/telegram", json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            tok = r.json().get("token")
            cfg["init_data"] = init_data
            if tok:
                cfg["token"] = tok
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=4)
            log("[DRAM] >> SUKSES login & menyegarkan token DRAM! <<")
            return True
    except Exception as e:
        log(f"[DRAM] Error: {e}")
    return False

async def refresh_mrg(client):
    try:
        log("[MRG] Mengambil token baru via @mrgminerbot...")
        bot_input = await client.get_input_entity("mrgminerbot")
        app = types.InputBotAppShortName(bot_id=bot_input, short_name="app")
        res = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot_input,
            app=app,
            platform="android"
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "mrg", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=4)
            log("[MRG] >> SUKSES menyegarkan initData MRG! <<")
            return True
    except Exception as e:
        log(f"[MRG] Error: {e}")
    return False

async def refresh_victor(client):
    try:
        log("[Victor] Mengambil token baru via @VictorsCompanybot...")
        bot_input = await client.get_input_entity("VictorsCompanybot")
        app = types.InputBotAppShortName(bot_id=bot_input, short_name="app")
        res = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot_input,
            app=app,
            platform="android"
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "victor", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["authorization"] = f"tma {init_data}"
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=4)
            log("[Victor] >> SUKSES menyegarkan authorization Victor! <<")
            return True
    except Exception as e:
        log(f"[Victor] Error: {e}")
    return False

async def refresh_diggo(client):
    try:
        log("[Diggo] Mengambil token baru via @Diggominer_bot...")
        bot = await client.get_entity("Diggominer_bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://app.diggocoin.com/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        headers = {
            "Origin": "https://app.diggocoin.com",
            "Referer": "https://app.diggocoin.com/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
        r = requests.post("https://app.diggocoin.com/api/auth/telegram", json={"initData": init_data}, headers=headers, timeout=15)
        if r.status_code == 200:
            tok = r.json().get("token")
            if tok:
                cfg_path = os.path.join(FARMERS_DIR, "diggo", "config.json")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r") as f:
                        cfg = json.load(f)
                    cfg["token"] = tok
                    with open(cfg_path, "w") as f:
                        json.dump(cfg, f, indent=4)
                    log("[Diggo] >> SUKSES login & menyegarkan token Diggo! <<")
                    return True
    except Exception as e:
        log(f"[Diggo] Error: {e}")
    return False

async def refresh_mainet(client):
    try:
        log("[mAInet] Mengambil token baru via @mainetbot...")
        bot = await client.get_entity("mainetbot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://web.mainet.io/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        sys.path.append(os.path.join(FARMERS_DIR, "mainet"))
        from farmer import solve_chq

        url = "https://api.mainet.io/api/account/login"
        headers = {
            "Origin": "https://web.mainet.io",
            "Referer": "https://web.mainet.io/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "x-app": "mainet_server",
            "x-cv": "13"
        }
        payload = {"init_data": init_data, "referrer": ""}
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            data = r.json()
            chq = data.get("chq")
            if chq:
                chr_val = solve_chq(chq)
                if chr_val:
                    payload["chr"] = int(chr_val) if chr_val.isdigit() else chr_val
                    r2 = requests.post(url, json=payload, headers=headers, timeout=15)
                    data = r2.json()
            tok = data.get("access_token")
            if tok:
                cfg_path = os.path.join(FARMERS_DIR, "mainet", "config.json")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r") as f:
                        cfg = json.load(f)
                    cfg["token"] = f"Bearer {tok}"
                    cfg["init_data"] = init_data
                    with open(cfg_path, "w") as f:
                        json.dump(cfg, f, indent=4)
                    log("[mAInet] >> SUKSES menyelesaikan CHQ & menyimpan JWT mAInet! <<")
                    return True
    except Exception as e:
        log(f"[mAInet] Error: {e}")
    return False

async def refresh_epsilon(client):
    try:
        log("[Epsilon] Mengambil token baru via @Epsiloncrypto_bot...")
        bot = await client.get_entity("Epsiloncrypto_bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://mining.epsilons.io/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        headers = {
            "Origin": "https://mining.epsilons.io",
            "Referer": "https://mining.epsilons.io/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
        r = requests.post("https://api.epsilons.io/api/v1/auth/telegram", json={"initData": init_data}, headers=headers, timeout=15)
        if r.status_code == 200:
            tok = r.json().get("token")
            if tok:
                cfg_path = os.path.join(FARMERS_DIR, "epsilon", "config.json")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r") as f:
                        cfg = json.load(f)
                    cfg["token"] = tok
                    cfg["init_data"] = init_data
                    with open(cfg_path, "w") as f:
                        json.dump(cfg, f, indent=4)
                    log("[Epsilon] >> SUKSES menyegarkan token Epsilon (7 Hari)! <<")
                    return True
    except Exception as e:
        log(f"[Epsilon] Error: {e}")
    return False

async def refresh_grambuddies(client):
    try:
        log("[GramBuddies] Mengambil token baru via @GramBuddiesBot...")
        bot = await client.get_entity("GramBuddiesBot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://buddies.name.ng/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "grambuddies", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=4)
            log("[GramBuddies] >> SUKSES menyegarkan initData Gram Buddies! <<")
            return True
    except Exception as e:
        log(f"[GramBuddies] Error: {e}")
    return False

async def refresh_odra(client):
    try:
        log("[ODRA] Mengambil token baru via @ODRAcoinBot...")
        bot = await client.get_entity("ODRAcoinBot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://odra.onrender.com/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "odra", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=4)
            log("[ODRA] >> SUKSES menyegarkan initData ODRA! <<")
            return True
    except Exception as e:
        log(f"[ODRA] Error: {e}")
    return False

async def refresh_tomarket(client):
    try:
        log("[Tomarket] Mengambil token baru via @Tomarket_ai_bot...")
        bot = await client.get_entity("Tomarket_ai_bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://mini-app.tomarket.ai/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        headers = {
            "Origin": "https://mini-app.tomarket.ai",
            "Referer": "https://mini-app.tomarket.ai/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
        payload = {"init_data": init_data, "invite_code": "", "from": "", "is_bot": False}
        r = requests.post("https://api-web.tomarket.ai/tomarket-game/v1/user/login", json=payload, headers=headers, timeout=15)
        access_token = ""
        if r.status_code == 200 and r.json().get("status") == 0:
            access_token = r.json().get("data", {}).get("access_token", "")

        cfg_path = os.path.join(FARMERS_DIR, "tomarket", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            if access_token:
                cfg["access_token"] = access_token
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[Tomarket] >> SUKSES menyegarkan token & initData Tomarket! <<")
            return True
    except Exception as e:
        log(f"[Tomarket] Error: {e}")
    return False

async def refresh_crownminer(client):
    try:
        log("[CrownMiner] Mengambil token baru via @CrownMinerBot...")
        bot = await client.get_entity("CrownMinerBot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://test.crownville.online/crownminer-stage/game/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "crownminer", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[CrownMiner] >> SUKSES menyegarkan initData CrownMiner! <<")
            return True
    except Exception as e:
        log(f"[CrownMiner] Error: {e}")
    return False

async def refresh_lumetra(client):
    try:
        log("[LumeTRA] Mengambil token baru via @LUMETRAS_BOT...")
        bot = await client.get_input_entity("LUMETRAS_BOT")
        app = types.InputBotAppShortName(bot_id=bot, short_name="App")
        res = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot,
            app=app,
            platform="android",
            start_param="ref_8324041139"
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        qs = urllib.parse.parse_qs(init_data)
        u_obj = json.loads(qs.get("user", ["{}"])[0])
        payload = {
            "tg_id": u_obj.get("id"),
            "name": u_obj.get("first_name", "Local Miner"),
            "photo_url": u_obj.get("photo_url", ""),
            "startapp": "ref_8324041139",
            "init_data": init_data
        }
        headers = {
            "Origin": "https://web.lumetramine.com",
            "Referer": "https://web.lumetramine.com/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
        r = requests.post("https://api.lumetramine.com/api/login", json=payload, headers=headers, timeout=15)
        token = ""
        if r.status_code == 200 and r.json().get("code") == 1:
            token = r.json().get("data", {}).get("token", "")

        cfg_path = os.path.join(FARMERS_DIR, "lumetra", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            if token:
                cfg["token"] = token
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[LumeTRA] >> SUKSES menyegarkan JWT token & initData LumeTRA! <<")
            return True
    except Exception as e:
        log(f"[LumeTRA] Error: {e}")
    return False

async def refresh_mininggram(client):
    try:
        log("[MiningGRAM] Mengambil initData via @MiningGRAM_Bot...")
        bot = await client.get_entity("MiningGRAM_Bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://mining-gram-miniapp.pages.dev/?tab=mine",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        api_base = "https://mining-gram-worker.muhaisin0888.workers.dev"
        r = requests.post(f"{api_base}/api/auth", json={"initData": init_data}, headers={"Content-Type": "application/json"}, timeout=15)
        session_token = ""
        if r.status_code == 200:
            session_token = r.json().get("sessionToken", "")

        cfg_path = os.path.join(FARMERS_DIR, "mininggram", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            if session_token:
                cfg["session_token"] = session_token
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[MiningGRAM] >> SUKSES menyegarkan initData & sessionToken MiningGRAM! <<")
            return True
    except Exception as e:
        log(f"[MiningGRAM] Error: {e}")
    return False

async def refresh_minex(client):
    try:
        log("[MineX] Mengambil initData via @MineXton_bot...")
        bot = await client.get_input_entity("MineXton_bot")
        app = types.InputBotAppShortName(bot_id=bot, short_name="russia")
        res = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot,
            app=app,
            platform="android"
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "minex", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[MineX] >> SUKSES menyegarkan initData MineX! <<")
            return True
    except Exception as e:
        log(f"[MineX] Error: {e}")
    return False

async def refresh_vyq(client):
    try:
        log("[VYQ] Mengambil token baru via @VYQMiners_bot...")
        bot = await client.get_input_entity("VYQMiners_bot")
        app = types.InputBotAppShortName(bot_id=bot, short_name="app")
        res = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot,
            app=app,
            platform="android"
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        qs = urllib.parse.parse_qs(init_data)
        u_obj = json.loads(qs.get("user", ["{}"])[0])
        payload = {
            "tg_id": u_obj.get("id"),
            "name": u_obj.get("first_name", "Local Miner"),
            "photo_url": u_obj.get("photo_url", ""),
            "startapp": "",
            "init_data": init_data
        }
        headers = {
            "Origin": "https://web.vyqminer.top",
            "Referer": "https://web.vyqminer.top/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
        r = requests.post("https://api.vyqminer.top/api/login", json=payload, headers=headers, timeout=15)
        token = ""
        if r.status_code == 200 and r.json().get("code") == 1:
            token = r.json().get("data", {}).get("token", "")

        cfg_path = os.path.join(FARMERS_DIR, "vyq", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            if token:
                cfg["token"] = token
            with open(cfg_path, "w") as f:
                json.dump(cfg, f, indent=2)
            log("[VYQ] >> SUKSES menyegarkan JWT token & initData VYQ! <<")
            return True
    except Exception as e:
        log(f"[VYQ] Error: {e}")
    return False

async def refresh_pickaxeempire(client):
    try:
        log("[PickaxeEmpire] Mengambil initData via @PickaxeEmpireBot...")
        bot = await client.get_entity("PickaxeEmpireBot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://app.pickaxeempire.com/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "pickaxeempire", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            log("[PickaxeEmpire] >> SUKSES menyegarkan initData Pickaxe Empire! <<")
            return True
    except Exception as e:
        log(f"[PickaxeEmpire] Error: {e}")
    return False

async def refresh_monsterland(client):
    try:
        log("[Monsterland] Mengambil initData via @monsterland_bot...")
        bot = await client.get_input_entity("monsterland_bot")
        res = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot,
            app=types.InputBotAppShortName(bot_id=bot, short_name="play"),
            platform="android"
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "monsterland", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["authorization"] = f"tma {init_data}"
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            log("[Monsterland] >> SUKSES menyegarkan initData Monsterland! <<")
            return True
    except Exception as e:
        log(f"[Monsterland] Error: {e}")
    return False

async def refresh_crownville(client):
    try:
        log("[Crownville] Mengambil token baru via @Crownvillebot...")
        bot = await client.get_input_entity("Crownvillebot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://crownville.online/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "crownville", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log("[Crownville] >> SUKSES menyegarkan initData Crownville! <<")
            return True
    except Exception as e:
        log(f"[Crownville] Error: {e}")
    return False

async def refresh_chickenempire(client):
    try:
        log("[ChickenEmpire] Mengambil token baru via @chicken_empirebot...")
        bot = await client.get_input_entity("chicken_empirebot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://app.miniempire.app/miniapp/index.html?tid=1523&lang=en",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "chickenempire", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log("[ChickenEmpire] >> SUKSES menyegarkan initData Chicken Empire! <<")
            return True
    except Exception as e:
        log(f"[ChickenEmpire] Error: {e}")
    return False

async def refresh_minerxrealm(client):
    try:
        log("[MinerXRealm] Mengambil token baru via @MinerXRealmBot...")
        bot = await client.get_input_entity("MinerXRealmBot")
        async for m in client.iter_messages(bot, limit=5):
            if m.reply_markup and hasattr(m.reply_markup, 'rows'):
                for r in m.reply_markup.rows:
                    for b in r.buttons:
                        if b.text == '🎮 Open App':
                            res = await client(functions.messages.RequestWebViewRequest(
                                peer=bot,
                                bot=bot,
                                platform="android",
                                url=b.type.url,
                                reply_to=types.InputReplyToMessage(reply_to_msg_id=m.id)
                            ))
                            init_data = parse_init_data(res.url)
                            if not init_data:
                                return False
                            cfg_path = os.path.join(FARMERS_DIR, "minerxrealm", "config.json")
                            if os.path.exists(cfg_path):
                                with open(cfg_path, "r", encoding="utf-8") as f:
                                    cfg = json.load(f)
                                cfg["init_data"] = init_data
                                with open(cfg_path, "w", encoding="utf-8") as f:
                                    json.dump(cfg, f, indent=2)
                                log("[MinerXRealm] >> SUKSES menyegarkan initData MinerXRealm! <<")
                                return True
    except Exception as e:
        log(f"[MinerXRealm] Error: {e}")
    return False

async def refresh_edgeofempire(client):
    try:
        log("[EdgeOfEmpire] Mengambil token baru via @EdgeOfEmpireBot...")
        bot = await client.get_input_entity("EdgeOfEmpireBot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://edgeofempire.club/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False
        cfg_path = os.path.join(FARMERS_DIR, "edgeofempire", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log("[EdgeOfEmpire] >> SUKSES menyegarkan initData Edge of Empire! <<")
            return True
    except Exception as e:
        log(f"[EdgeOfEmpire] Error: {e}")
    return False

async def refresh_aicminer(client):
    try:
        log("[AICMiner] Mengambil token baru via @Aicminer_bot...")
        bot = await client.get_input_entity("Aicminer_bot")
        async for m in client.iter_messages(bot, limit=10):
            if m.reply_markup:
                for row in m.reply_markup.rows:
                    for b in row.buttons:
                        if isinstance(b, types.InlineKeyboardButtonWebView):
                            res = await client(functions.messages.RequestWebViewRequest(
                                peer=bot,
                                bot=bot,
                                platform="android",
                                url=b.url,
                                from_bot_menu=False,
                                reply_to=types.InputReplyToMessage(reply_to_msg_id=m.id)
                            ))
                            init_data = parse_init_data(res.url)
                            if not init_data:
                                return False
                            cfg_path = os.path.join(FARMERS_DIR, "aicminer", "config.json")
                            if os.path.exists(cfg_path):
                                with open(cfg_path, "r", encoding="utf-8") as f:
                                    cfg = json.load(f)
                                cfg["init_data"] = init_data
                                with open(cfg_path, "w", encoding="utf-8") as f:
                                    json.dump(cfg, f, indent=2)
                                log("[AICMiner] >> SUKSES menyegarkan initData AIC Miner! <<")
                                return True
    except Exception as e:
        log(f"[AICMiner] Error: {e}")
    return False

async def refresh_catopia(client):
    try:
        log("[Catopia] Mengambil token baru via @catopia_game_bot...")
        bot = await client.get_entity("catopia_game_bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://game.catopia.io/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "catopia", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log("[Catopia] >> SUKSES menyegarkan initData Catopia! <<")
            return True
    except Exception as e:
        log(f"[Catopia] Error: {e}")
    return False

async def refresh_clayton(client):
    try:
        log("[Clayton] Mengambil token baru via @claytongame_bot...")
        bot = await client.get_entity("claytongame_bot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://tonclayton.fun/",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "clayton", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log("[Clayton] >> SUKSES menyegarkan initData Clayton! <<")
            return True
    except Exception as e:
        log(f"[Clayton] Error: {e}")
    return False

async def refresh_deepmine(client):
    try:
        log("[DeepMine] Mengambil initData baru via @MineDeepBot...")
        bot = await client.get_input_entity("MineDeepBot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://linobot.ir/mine/?v=69",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "deepmine", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log("[DeepMine] >> SUKSES menyegarkan initData Deep Mine! <<")
            return True
    except Exception as e:
        log(f"[DeepMine] Error: {e}")
    return False

async def refresh_clone_vyq(client, folder_name, bot_username, domain_api, domain_web):
    try:
        log(f"[{folder_name.upper()}] Mengambil token baru via @{bot_username}...")
        bot = await client.get_input_entity(bot_username)
        app = types.InputBotAppShortName(bot_id=bot, short_name="app")
        res = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot,
            app=app,
            platform="android"
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        qs = urllib.parse.parse_qs(init_data)
        u_obj = json.loads(qs.get("user", ["{}"])[0])
        payload = {
            "tg_id": u_obj.get("id"),
            "name": u_obj.get("first_name", "Local Miner"),
            "photo_url": u_obj.get("photo_url", ""),
            "startapp": "",
            "init_data": init_data
        }
        headers = {
            "Origin": f"https://{domain_web}",
            "Referer": f"https://{domain_web}/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
        r = requests.post(f"https://{domain_api}/api/login", json=payload, headers=headers, timeout=15)
        token = ""
        if r.status_code == 200 and r.json().get("code") == 1:
            token = r.json().get("data", {}).get("token", "")

        cfg_path = os.path.join(FARMERS_DIR, folder_name, "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            if token:
                cfg["token"] = token
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log(f"[{folder_name.upper()}] >> SUKSES menyegarkan JWT token & initData! <<")
            return True
    except Exception as e:
        log(f"[{folder_name.upper()}] Error: {e}")
    return False

async def refresh_ironoath(client):
    return await refresh_clone_vyq(client, "ironoath", "ironoathcompanybot", "api.ironoathcompany.top", "web.ironoathcompany.top")

async def refresh_roadsterboost(client):
    return await refresh_clone_vyq(client, "roadsterboost", "RoadsterBoost_bot", "api.roadsterboost.top", "web.roadsterboost.top")

async def refresh_lunaroreburrow(client):
    return await refresh_clone_vyq(client, "lunaroreburrow", "lunaroreburrowbot", "api.lunaroreburrow.top", "web.lunaroreburrow.top")

async def refresh_polaredenjungle(client):
    return await refresh_clone_vyq(client, "polaredenjungle", "polaredenjunglebot", "api.polaredenjungle.top", "web.polaredenjungle.top")

async def refresh_gram24(client):
    try:
        log("[Gram24] Mengambil token baru via @Gram24MiningBot...")
        bot = await client.get_input_entity("Gram24MiningBot")
        res = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            url="https://app.miniempire.app/miniapp/index.html?tid=2176&lang=en",
            from_bot_menu=False
        ))
        init_data = parse_init_data(res.url)
        if not init_data:
            return False

        cfg_path = os.path.join(FARMERS_DIR, "gram24", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["init_data"] = init_data
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            log("[Gram24] >> SUKSES menyegarkan initData Gram24! <<")
            return True
    except Exception as e:
        log(f"[Gram24] Error: {e}")
    return False

async def run_cycle():
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        log("ERROR: Client Telegram belum terotorisasi! Periksa session file.")
        await client.disconnect()
        return False

    log("=== MEMULAI SIKLUS MASTER PENYEGARAN TOKEN OTOMATIS (23 BOT) ===")
    
    tasks = [
        ("VYRO", refresh_vyro),
        ("ATF", refresh_atf),
        ("DRAM", refresh_dram),
        # ("MRG", refresh_mrg),  # Flagged SCAM by Telegram
        # ("Victor", refresh_victor),  # Flagged SCAM by Telegram
        ("Diggo", refresh_diggo),
        ("mAInet", refresh_mainet),
        ("Epsilon", refresh_epsilon),
        ("GramBuddies", refresh_grambuddies),
        ("ODRA", refresh_odra),
        ("Tomarket", refresh_tomarket),
        ("CrownMiner", refresh_crownminer),
        ("Crownville", refresh_crownville),
        ("LumeTRA", refresh_lumetra),
        ("MiningGRAM", refresh_mininggram),
        ("MineX", refresh_minex),
        ("VYQ", refresh_vyq),
        ("PickaxeEmpire", refresh_pickaxeempire),
        ("Monsterland", refresh_monsterland),
        ("ChickenEmpire", refresh_chickenempire),
        ("MinerXRealm", refresh_minerxrealm),
        ("EdgeOfEmpire", refresh_edgeofempire),
        ("AICMiner", refresh_aicminer),
        ("Catopia", refresh_catopia),
        ("Clayton", refresh_clayton),
        ("DeepMine", refresh_deepmine),
        ("IronOath", refresh_ironoath),
        ("RoadsterBoost", refresh_roadsterboost),
        ("LunarOreBurrow", refresh_lunaroreburrow),
        ("PolarEdenJungle", refresh_polaredenjungle),
        ("Gram24", refresh_gram24)
    ]

    for name, func in tasks:
        try:
            await func(client)
        except Exception as e:
            log(f"[{name}] Exception: {e}")
        await asyncio.sleep(1.5)

    await client.disconnect()
    log("=== SIKLUS MASTER SELESAI. Semua 18 bot berhasil disinkronisasi dengan Telegram! ===")
    return True

async def main_loop():
    log("=== Telegram WebApp Master Auto-Token Generator Daemon Dimulai ===")
    while True:
        try:
            await run_cycle()
        except Exception as e:
            log(f"Exception di siklus utama: {e}")
        log(f"Menunggu {REFRESH_INTERVAL_SECONDS // 60} menit untuk siklus berikutnya...")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        asyncio.run(run_cycle())
    else:
        asyncio.run(main_loop())
