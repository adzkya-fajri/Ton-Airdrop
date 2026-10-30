import json
import os
import sys
import time
import random
import datetime
import uuid
import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmer.log")
BASE_URL = "https://dram.faithton.online"

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

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        log(f"WARN: Gagal menyimpan config.json: {e}")

def get_headers(cfg):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
    }
    tok = cfg.get("token", "").strip()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return headers

def login(cfg):
    init_data = cfg.get("init_data", "").strip()
    if not init_data:
        log("ERROR: init_data kosong di config.json!")
        return False, None

    url = f"{BASE_URL}/api/auth/telegram"
    device = cfg.get("device", {
        "deviceUuid": str(uuid.uuid4()),
        "persistent": True,
        "screen": "390x844x24@3",
        "platform": "Linux armv8l",
        "timezone": "Asia/Jakarta",
        "cores": 8,
        "canvas": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "webgl": "Adreno (TM) 740",
        "tgPlatform": "android"
    })

    headers = get_headers(cfg)
    headers.pop("Authorization", None)

    payload = {
        "initData": init_data,
        "device": device
    }

    try:
        log("Melakukan autentikasi Telegram WebApp ke DRAM server...")
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            tok = data.get("token")
            if tok:
                cfg["token"] = tok
                save_config(cfg)
                log(f">> LOGIN BERHASIL! Token sesi disimpan (User: {data.get('profile', {}).get('name')}) <<")
                return True, data.get("profile")
            else:
                log(f">> Login gagal: tidak ada token dalam respon: {data} <<")
                return False, None
        else:
            log(f">> Login gagal ({r.status_code}): {r.text[:150]} <<")
            return False, None
    except Exception as e:
        log(f">> Exception saat login DRAM: {e} <<")
        return False, None

def get_profile(cfg):
    url = f"{BASE_URL}/api/profile"
    headers = get_headers(cfg)

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return True, r.json()
        elif r.status_code == 401:
            log(">> Sesi token kadaluarsa (401), mencoba login ulang... <<")
            ok, prof = login(cfg)
            if ok:
                new_cfg = load_config()
                return get_profile(new_cfg)
            return False, None
        else:
            log(f">> Gagal mengambil profile ({r.status_code}): {r.text[:150]} <<")
            return False, None
    except Exception as e:
        log(f">> Exception saat get_profile DRAM: {e} <<")
        return False, None

def claim_mining(cfg):
    url = f"{BASE_URL}/api/mining/claim"
    headers = get_headers(cfg)
    headers["idempotency-key"] = str(uuid.uuid4())

    try:
        log("Mengeksekusi klaim reward mining DRAM...")
        r = requests.post(url, headers=headers, json={}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            prof = data.get("profile", {})
            name = prof.get("name", "User")
            bal = prof.get("balance", 0)
            lvl = prof.get("level", 1)
            daily = prof.get("dailyOutput", 300)
            credited = data.get("creditedUnits", 0) / 1000.0

            log("=" * 50)
            log(">> KLAIM DRAM BERHASIL! <<")
            log(f"Player        : {name} (ID: {prof.get('userId')})")
            log(f"Reward Diklaim: +{credited:.2f} DRAM")
            log(f"Total Saldo   : {bal:.2f} DRAM (Level {lvl})")
            log(f"Mining Rate   : +{daily:.2f} DRAM/hari")
            log("=" * 50)
            return True, data
        elif r.status_code == 401:
            log(">> Token 401 saat klaim, mencoba login ulang... <<")
            ok, prof = login(cfg)
            if ok:
                new_cfg = load_config()
                return claim_mining(new_cfg)
            return False, None
        else:
            log(f">> Gagal klaim DRAM ({r.status_code}): {r.text[:150]} <<")
            return False, None
    except Exception as e:
        log(f">> Exception saat klaim DRAM: {e} <<")
        return False, None

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== DRAM Miner Auto-Farmer Started ===")

    # Pastikan login valid
    if not cfg.get("token"):
        ok, prof = login(cfg)
        if not ok:
            log("Gagal inisialisasi sesi awal!")
            sys.exit(1)
        cfg = load_config()

    if once:
        log("Mode: One-Shot Manual Test")
        claim_mining(cfg)
        return

    while True:
        try:
            ok, prof = get_profile(cfg)
            if not ok or not prof:
                log("Gagal mendapatkan status mining, coba lagi dalam 60 detik...")
                time.sleep(60)
                cfg = load_config()
                continue

            unclaimed = prof.get("unclaimed", 0)
            elapsed = prof.get("elapsedSeconds", 0)
            cycle = prof.get("cycleSeconds", 14400)
            min_claim = prof.get("minimumClaimSeconds", 14400)

            # Jika saldo unclaimed sudah ada atau siklus 4 jam terpenuhi, klaim!
            if unclaimed > 0 or elapsed >= min_claim:
                claim_mining(cfg)
                # Ambil profil segar setelah klaim
                time.sleep(3)
                ok, prof = get_profile(cfg)
                if prof:
                    elapsed = prof.get("elapsedSeconds", 0)
                    cycle = prof.get("cycleSeconds", 14400)
                    min_claim = prof.get("minimumClaimSeconds", 14400)

            # Hitung sisa waktu siklus berikutnya
            remaining = max(min_claim - elapsed, 60)
            jitter = random.randint(30, 180)  # Tambah jeda acak 30-180 detik
            total_sleep = remaining + jitter
            next_time = datetime.datetime.now() + datetime.timedelta(seconds=total_sleep)

            log(f"Siklus mining berjalan: {elapsed}/{min_claim}s. Tidur ~{total_sleep//60} menit. Klaim berikutnya: {next_time.strftime('%H:%M:%S')}")
            time.sleep(total_sleep)

        except KeyboardInterrupt:
            log("Farmer dihentikan oleh user.")
            break
        except Exception as e:
            log(f"Unexpected loop exception: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
