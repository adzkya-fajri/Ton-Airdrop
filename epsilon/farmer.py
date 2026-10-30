import json
import os
import sys
import time
import random
import datetime
import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmer.log")
BASE_URL = "https://api.epsilons.io/api/v1"

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
        log(f"Gagal simpan config: {e}")

def get_headers(cfg):
    token = cfg.get("token", "").strip().replace("Bearer ", "")
    headers = {
        "Origin": "https://mining.epsilons.io",
        "Referer": "https://mining.epsilons.io/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json",
        "Accept": "*/*"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def refresh_token(cfg):
    init_data = cfg.get("init_data")
    if not init_data:
        log("ERROR: init_data tidak ada di config.json untuk re-login.")
        return False

    url = f"{BASE_URL}/auth/telegram"
    headers = {
        "Origin": "https://mining.epsilons.io",
        "Referer": "https://mining.epsilons.io/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json"
    }

    try:
        log("Memperbarui token otentikasi Epsilon via initData...")
        res = requests.post(url, headers=headers, json={"initData": init_data}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            new_token = data.get("token")
            if new_token:
                cfg["token"] = new_token
                save_config(cfg)
                log(">> Token Epsilon berhasil diperbarui otomatis (Aktif 7 Hari)! <<")
                return True
        log(f">> Re-login gagal ({res.status_code}): {res.text} <<")
        return False
    except Exception as e:
        log(f">> Exception saat refresh_token: {e} <<")
        return False

def get_mining_status(cfg):
    url = f"{BASE_URL}/mining"
    headers = get_headers(cfg)
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 401:
            log("Token kadaluarsa. Mencoba refresh token...")
            if refresh_token(cfg):
                headers = get_headers(cfg)
                res2 = requests.get(url, headers=headers, timeout=15)
                if res2.status_code == 200:
                    return res2.json()
            return None
        else:
            log(f">> Gagal get mining status ({res.status_code}): {res.text[:120]} <<")
            return None
    except Exception as e:
        log(f">> Exception saat get_mining_status: {e} <<")
        return None

def start_mining(cfg):
    url = f"{BASE_URL}/mining/start"
    headers = get_headers(cfg)
    try:
        log("Menjalankan siklus penambangan Epsilon (Start Mining)...")
        res = requests.post(url, headers=headers, json={}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            ready_at = data.get("readyAt", 0)
            dt_ready = datetime.datetime.fromtimestamp(ready_at / 1000) if ready_at else None
            dt_str = dt_ready.strftime('%H:%M:%S') if dt_ready else 'Unknown'
            log(f">> MINING BERHASIL DIMULAI! Siap klaim pada pukul: {dt_str} <<")
            return True, data
        else:
            log(f">> Gagal start mining ({res.status_code}): {res.text[:120]} <<")
            return False, res.text
    except Exception as e:
        log(f">> Exception saat start mining: {e} <<")
        return False, str(e)

def claim_mining(cfg):
    url = f"{BASE_URL}/mining/claim"
    headers = get_headers(cfg)
    try:
        log("Mengeksekusi klaim mining reward Epsilon...")
        res = requests.post(url, headers=headers, json={}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            reward = data.get("reward", 0)
            balance = data.get("balance", 0)
            log("=" * 50)
            log(">> KLAIM EPSILON BERHASIL! <<")
            log(f"Reward Masuk : +{reward} EPS")
            log(f"Total Saldo  : {balance:.4f} EPS")
            log("=" * 50)
            # Begitu berhasil klaim, langsung mulai siklus berikutnya!
            start_mining(cfg)
            return True, data
        else:
            log(f">> Gagal claim mining ({res.status_code}): {res.text[:120]} <<")
            return False, res.text
    except Exception as e:
        log(f">> Exception saat claim mining: {e} <<")
        return False, str(e)

def process_mining(cfg):
    status_data = get_mining_status(cfg)
    if not status_data:
        return

    m_status = status_data.get("status", "UNKNOWN")
    balance = status_data.get("balance", 0)
    ready_at = status_data.get("readyAt") or 0
    server_now = status_data.get("serverNow") or int(time.time() * 1000)

    if m_status == "READY":
        claim_mining(cfg)
    elif m_status == "IDLE":
        start_mining(cfg)
    elif m_status == "MINING":
        if server_now >= ready_at:
            claim_mining(cfg)
        else:
            rem_sec = max(0, int((ready_at - server_now) / 1000))
            rem_h = rem_sec // 3600
            rem_m = (rem_sec % 3600) // 60
            rem_s = rem_sec % 60
            dt_ready = datetime.datetime.fromtimestamp(ready_at / 1000)
            log(f"[Mining Berjalan] Sisa: {rem_h}j {rem_m}m {rem_s}s (Selesai: {dt_ready.strftime('%H:%M:%S')}). Saldo: {balance:.4f} EPS")
    else:
        log(f"Status tidak dikenal: {m_status}")

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== Epsilon Miner Auto-Farmer Started ===")

    if once:
        log("Mode: One-Shot Manual Test")
        process_mining(cfg)
        return

    interval_sec = cfg.get("check_interval_seconds", 600)

    while True:
        try:
            process_mining(cfg)
            jitter = random.randint(10, 45)
            time.sleep(interval_sec + jitter)
        except KeyboardInterrupt:
            log("Farmer dihentikan.")
            break
        except Exception as e:
            log(f"Unexpected loop exception: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
