#!/usr/bin/env python3
"""
ATF Miner Pure Keep-Alive (Anti-Offline Mode)
Tujuan:
1. Menjaga status akun selalu ONLINE di server ATF agar Hashrate (HS) tidak drop (khusus akun < 200 lvl)
2. TIDAK PERNAH melakukan klaim koin (action=claim dinonaktifkan total untuk mencegah deteksi bot)
3. Klaim koin tetap dilakukan 100% manual oleh pengguna di mini-app resmi
"""

import json
import os
import sys
import time
import random
import uuid
import base64
import datetime
import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmer.log")

def log(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(formatted + "\n")
            f.flush()
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_PATH):
        log(f"ERROR: File {CONFIG_PATH} tidak ditemukan!")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def get_headers(cfg):
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://atfminers.asloni.online",
        "Referer": "https://atfminers.asloni.online/miner/index.html?v=1786140012",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"),
        "X-Requested-With": "XMLHttpRequest",
        "X-Telegram-Init-Data": cfg["init_data"],
        "X-ATF-TMA-Session": cfg.get("tma_session", "")
    }
    
    cookies = []
    if cfg.get("cookie"):
        cookies.append(cfg["cookie"])
    if cfg.get("tma_session"):
        cookies.append(f"atf_tma_session={cfg['tma_session']}")
    if cookies:
        headers["Cookie"] = "; ".join(cookies)
    return headers

def get_session_expiry(token):
    try:
        part0 = token.split(".")[0]
        padded = part0 + "=" * (-len(part0) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        return payload.get("exp", 0)
    except Exception:
        return 0

def auto_refresh_session(cfg):
    log("[Auth] Memperbarui tma_session secara otomatis via action=login...")
    t = int(time.time() * 1000)
    url = f"https://atfminers.asloni.online/miner/index.php?action=login&t={t}"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "https://atfminers.asloni.online",
        "Referer": "https://atfminers.asloni.online/miner/index.html?v=1786140012",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"),
        "X-Telegram-Init-Data": cfg["init_data"],
        "Cookie": cfg.get("cookie", "")
    }
    payload = {
        "initData": cfg["init_data"],
        "request_id": f"rq-{t}-{str(uuid.uuid4())[:8]}",
        "device_id": "dev-" + str(uuid.uuid4()).replace("-", "")[:16],
        "tg_id": cfg.get("tg_id", 7672016530),
        "username": cfg.get("username", "Zelx_arthur")
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success" and data.get("tma_session_token"):
                new_token = data["tma_session_token"]
                cfg["tma_session"] = new_token
                with open(CONFIG_PATH, "w") as f:
                    json.dump(cfg, f, indent=4)
                exp = get_session_expiry(new_token)
                exp_str = datetime.datetime.fromtimestamp(exp).strftime("%d/%m/%Y %H:%M:%S") if exp else "48 jam"
                log(f"[Auth] >> SUKSES! tma_session baru berhasil dibuat otomatis (Aktif s/d {exp_str}) <<")
                return True
            else:
                log(f"[Auth] Respon gagal saat refresh: {data}")
        elif res.status_code == 403:
            log("[Auth] Cloudflare challenge terdeteksi saat login.")
        else:
            log(f"[Auth] Gagal refresh session (HTTP {res.status_code}): {res.text[:120]}")
    except Exception as e:
        log(f"[Auth] Error network saat refresh: {e}")
    return False

def activate_boost(cfg, display_preview=0.0, retry=True):
    """
    Kirim activate_boost ke server ATF.
    Ini adalah yang mengupdate status 'online' / unfreeze mining untuk non-buyer.
    Harus dipanggil setiap siklus boost_cycle_seconds (~8 detik per tap, efektifnya per interval sync).
    """
    t = int(time.time() * 1000)
    url = f"https://atfminers.asloni.online/miner/index.php?action=activate_boost&t={t}"
    headers = get_headers(cfg)
    payload = {
        "initData": cfg["init_data"],
        "request_id": f"rq-{t}-{str(uuid.uuid4())[:8]}",
        "device_id": "dev-" + str(uuid.uuid4()).replace("-", "")[:16],
        "tg_id": cfg.get("tg_id", 7672016530),
        "display_preview": round(float(display_preview), 4)
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                boost_until = data.get("user", {}).get("boost_active_until", 0)
                boost_str = datetime.datetime.fromtimestamp(boost_until).strftime("%H:%M:%S") if boost_until else "-"
                log(f"[Boost] ✅ activate_boost SUKSES | Aktif s/d: {boost_str}")
                return True, data
            else:
                reason = str(data.get("reason", data.get("message", data)))
                # Jika session expired, refresh dulu
                if retry and ("tma_session" in str(reason).lower() or "unauthorized" in str(reason).lower()):
                    if auto_refresh_session(cfg):
                        return activate_boost(cfg, display_preview, retry=False)
                if "tap_mode_active" in str(reason).lower():
                    log(f"[Boost] Akun dalam mode Tap v2 (tap_mode_active). Manual boost tidak diperlukan, mining & reward berjalan via Auto-Tap.")
                    return False, "tap_mode_active"
                log(f"[Boost] activate_boost gagal: {reason}")
                return False, data
        elif res.status_code in (401, 403) and retry:
            if auto_refresh_session(cfg):
                return activate_boost(cfg, display_preview, retry=False)
        log(f"[Boost] HTTP {res.status_code}: {res.text[:100]}")
        return False, None
    except Exception as e:
        log(f"[Boost] Exception: {e}")
        return False, None

def record_daily_interaction(cfg, foreground_seconds=None):
    """
    Kirim record_daily_interaction untuk update activity score nonbuyer.
    Membantu menaikkan nonbuyer_activity_score_24h agar mining tidak difreeze.
    """
    t = int(time.time() * 1000)
    url = f"https://atfminers.asloni.online/miner/index.php?action=record_daily_interaction&t={t}"
    headers = get_headers(cfg)
    # Simulasi interaksi wajar: ~30-120 detik foreground, beberapa menu navigation
    if foreground_seconds is None:
        foreground_seconds = random.randint(30, 120)
    payload = {
        "initData": cfg["init_data"],
        "request_id": f"rq-{t}-{str(uuid.uuid4())[:8]}",
        "device_id": "dev-" + str(uuid.uuid4()).replace("-", "")[:16],
        "tg_id": cfg.get("tg_id", 7672016530),
        "foreground_seconds": foreground_seconds,
        "scroll_pixels": random.randint(100, 800),
        "unique_menus": random.randint(2, 5),
        "menu_changes": random.randint(3, 8),
        "trusted_input": 1
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success" and data.get("qualified"):
                log(f"[Activity] ✅ Daily interaction tercatat (qualified=true)")
                return True
            # Tidak qualified juga OK — server menerima request
            return True
        return False
    except Exception as e:
        log(f"[Activity] Exception: {e}")
        return False

def record_navigation_batch(cfg, delta=None):
    """
    Kirim record_navigation_batch untuk meniru navigasi tab/menu mini-app.
    Menghilangkan kecurigaan non-interactive headless client.
    """
    if delta is None:
        delta = random.randint(2, 6)
    t = int(time.time() * 1000)
    url = f"https://atfminers.asloni.online/miner/index.php?action=record_navigation_batch&t={t}"
    headers = get_headers(cfg)
    payload = {
        "initData": cfg["init_data"],
        "request_id": f"rq-{t}-{str(uuid.uuid4())[:8]}",
        "device_id": "dev-" + str(uuid.uuid4()).replace("-", "")[:16],
        "tg_id": cfg.get("tg_id", 7672016530),
        "delta": delta,
        "batch_id": "b_" + str(uuid.uuid4()).replace("-", "")[:12]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return True
    except Exception:
        pass
    return False

def sync_state(cfg, retry=True):
    # Cek masa berlaku session sebelum request (proaktif refresh jika sisa < 1 jam)
    cur_exp = get_session_expiry(cfg.get("tma_session", ""))
    if cur_exp and (cur_exp - time.time() < 3600):
        log("[Auth] Token mendekati kadaluarsa (< 1 jam tersisa). Melakukan auto-refresh proaktif...")
        auto_refresh_session(cfg)

    t = int(time.time() * 1000)
    url = f"https://atfminers.asloni.online/miner/index.php?action=sync_mining_state&t={t}"
    headers = get_headers(cfg)
    payload = {
        "initData": cfg["init_data"],
        "request_id": str(uuid.uuid4()),
        "device_id": "dev-" + str(uuid.uuid4()).replace("-", "")[:16],
        "tg_id": cfg.get("tg_id", 7672016530),
        "client_boost_cycle_seconds": 0
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                user = data.get("user", {})
                mined = user.get("mined_balance", "0")
                pending = user.get("pending_reward", 0)
                level = user.get("miner_level", 0)
                score = user.get("nonbuyer_activity_score_24h", 0)
                frozen = user.get("mining_frozen", 0)
                boost_until = user.get("boost_active_until", 0)
                boost_ready = user.get("boost_ready_at", 0)
                now_ts = int(time.time())

                if frozen:
                    rule = user.get("nonbuyer_rule_label", "frozen")
                    log(f"[Keep-Alive] 🟢 SYNC OK | Lvl {level} | Saldo: {mined} ATF | Pending: +{pending:.4f} | Score: {score} | ⛔ FROZEN ({rule})")
                else:
                    boost_str = ""
                    if boost_until and boost_until > now_ts:
                        boost_str = f" | Boost: s/d {datetime.datetime.fromtimestamp(boost_until).strftime('%H:%M:%S')}"
                    elif boost_ready and boost_ready <= now_ts:
                        boost_str = " | Boost: SIAP"
                    log(f"[Keep-Alive] 🟢 ONLINE | Lvl {level} | Saldo: {mined} ATF | Pending: +{pending:.4f} | Score: {score}{boost_str}")
                return True, data
            else:
                reason = str(data.get("reason", "")).lower()
                if retry and ("tma_session" in reason or "unauthorized" in reason or "auth" in reason):
                    log(f"[Auth] Sesi kadaluarsa ({reason}). Menjalankan pemulihan otomatis...")
                    if auto_refresh_session(cfg):
                        return sync_state(cfg, retry=False)
                log(f"[Keep-Alive] Respon server: {data}")
                return False, data
        elif res.status_code in (401, 403) and retry:
            log(f"[Auth] HTTP {res.status_code} terdeteksi. Mencoba auto-refresh auth...")
            if auto_refresh_session(cfg):
                return sync_state(cfg, retry=False)
            log(f"[Keep-Alive] HTTP Error {res.status_code}: {res.text[:120]}")
            return False, None
        else:
            log(f"[Keep-Alive] HTTP Error {res.status_code}: {res.text[:120]}")
            return False, None
    except Exception as e:
        log(f"[Keep-Alive] Network exception: {e}")
        return False, str(e)

def process_auto_tap(cfg):
    try:
        t = int(time.time() * 1000)
        client_inst = cfg.get("tap_client_id")
        if not client_inst:
            client_inst = "c_" + str(uuid.uuid4()).replace("-", "")[:16]
            cfg["tap_client_id"] = client_inst
            try:
                with open(CONFIG_PATH, "w") as f:
                    json.dump(cfg, f, indent=4)
            except Exception:
                pass

        headers = get_headers(cfg)
        state_url = f"https://atfminers.asloni.online/miner/index.php?action=tap_v2_state&t={t}"
        state_payload = {
            "initData": cfg["init_data"],
            "request_id": f"rq-{t}-{str(uuid.uuid4())[:8]}",
            "device_id": "dev-" + str(uuid.uuid4()).replace("-", "")[:16],
            "tg_id": cfg.get("tg_id", 7672016530),
            "client_instance": client_inst
        }
        r1 = requests.post(state_url, headers=headers, json=state_payload, timeout=15)
        if r1.status_code != 200:
            return False
        d1 = r1.json()
        if d1.get("status") != "success":
            return False

        energy = float(d1.get("energy", 0))
        max_energy = int(d1.get("max_energy", 2591))
        cost = float(d1.get("energy_cost", 10))
        nonce = d1.get("session_nonce")
        seq = (d1.get("last_seq") or 0) + 1

        available_taps = int(energy // cost)
        if available_taps < 20:
            return False

        # Batasi batch 50-70 tap agar natural dan efisien
        tap_count = min(available_taps, random.randint(50, 70))
        # Server rate limit max 8 taps/sec. Tunggu durasi natural (~6 tap/sec)
        wait_sec = max(6, int(tap_count / 5.5))
        time.sleep(wait_sec)

        t2 = int(time.time() * 1000)
        sync_url = f"https://atfminers.asloni.online/miner/index.php?action=tap_v2_sync&t={t2}"
        sync_payload = {
            "initData": cfg["init_data"],
            "request_id": f"rq-{t2}-{str(uuid.uuid4())[:8]}",
            "device_id": "dev-" + str(uuid.uuid4()).replace("-", "")[:16],
            "tg_id": cfg.get("tg_id", 7672016530),
            "client_instance": client_inst,
            "session_nonce": nonce,
            "seq": seq,
            "batch_id": "b_" + str(uuid.uuid4()).replace("-", "")[:12],
            "taps": tap_count
        }
        r2 = requests.post(sync_url, headers=headers, json=sync_payload, timeout=15)
        if r2.status_code == 200:
            d2 = r2.json()
            if d2.get("status") == "success":
                accepted = d2.get("accepted", 0)
                reward = d2.get("reward", 0)
                rem_energy = d2.get("energy", 0)
                pending = d2.get("pending_reward", 0)
                log(f"[Auto-Tap] ⚡ Tap {accepted}x Sukses (+{reward:.4f} ATF) | Sisa Energy: {rem_energy}/{max_energy} | Pending: +{pending:.4f}")
                return True
        return False
    except Exception as e:
        log(f"[Auto-Tap] Exception: {e}")
        return False

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== ATF Miner Keep-Alive & Auto-Tap Daemon Started ===")
    log("Mode: Online Heartbeat + Auto-Tap Energy + Boost Activate (TIDAK ADA KLAIM KOIN - 100% AMAN)")

    if once:
        sync_state(cfg)
        process_auto_tap(cfg)
        return

    keepalive_interval = cfg.get("keepalive_interval_seconds", 120)

    # Counter untuk tahu kapan harus kirim daily interaction (~setiap 20 menit)
    last_daily_interaction = 0
    DAILY_INTERACTION_INTERVAL = 1200  # 20 menit
    tap_mode_detected = False

    while True:
        try:
            # Reload config secara dinamis jika ada update token
            try:
                cfg = load_config()
            except Exception:
                pass

            # Kirim heartbeat agar status mining tetap aktif dan Hashrate tidak drop
            ok, sync_data = sync_state(cfg)

            if ok and sync_data:
                user = sync_data.get("user", {})
                frozen = user.get("mining_frozen", 0)
                boost_until = user.get("boost_active_until", 0)
                boost_ready = user.get("boost_ready_at", 0)
                pending = float(user.get("pending_reward", 0))
                now_ts = int(time.time())

                # Cek apakah perlu activate_boost:
                # - mining frozen, atau
                # - boost sudah habis dan akun tidak dalam tap_mode
                needs_boost = (
                    frozen or
                    ((not tap_mode_detected) and (
                        (boost_until == 0 and boost_ready <= now_ts) or
                        (boost_until > 0 and boost_until <= now_ts)
                    ))
                )

                if needs_boost:
                    log(f"[Boost] Mendeteksi mining {'FROZEN' if frozen else 'butuh boost baru'}. Mengirim activate_boost...")
                    b_ok, b_data = activate_boost(cfg, display_preview=pending)
                    if b_data == "tap_mode_active":
                        tap_mode_detected = True

            # Proses auto-tap untuk menghabiskan energi yang terisi penuh menjadi ATF reward
            process_auto_tap(cfg)

            # Kirim record_daily_interaction & navigation batch secara berkala untuk jaga presence
            now_ts = int(time.time())
            if now_ts - last_daily_interaction >= DAILY_INTERACTION_INTERVAL:
                record_daily_interaction(cfg)
                record_navigation_batch(cfg)
                last_daily_interaction = now_ts

            # Tidur dengan random jitter (misal 110s - 140s)
            jitter = random.randint(5, 25)
            sleep_time = keepalive_interval + jitter
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            log("Keep-alive dihentikan oleh user.")
            break
        except Exception as e:
            log(f"Loop unexpected exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
