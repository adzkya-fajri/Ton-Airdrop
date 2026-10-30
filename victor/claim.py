import json
import os
import sys
import time
import random
import datetime
import subprocess
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
        sample = {
            "authorization": "ISI_TOKEN_AUTHORIZATION_ANDA_DI_SINI",
            "x-human-pass": "",
            "min_interval_minutes": 60,
            "max_interval_minutes": 90,
            "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(sample, f, indent=4)
        log(f"File config.json baru dibuat di: {CONFIG_PATH}")
        log("Silakan edit config.json dan masukkan token Authorization Anda.")
        sys.exit(1)

    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)

    auth = cfg.get("authorization", "").strip()
    if not auth or "ISI_TOKEN" in auth or "[MASUKKAN_TOKEN" in auth:
        log("ERROR: Token authorization belum diisi dengan benar di config.json!")
        sys.exit(1)

    return cfg

def build_headers(cfg):
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Authorization": cfg["authorization"],
        "Content-Type": "application/json",
        "Origin": "https://app.victors.company",
        "Referer": "https://app.victors.company/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36")
    }
    if cfg.get("x-human-pass"):
        headers["x-human-pass"] = cfg["x-human-pass"].strip()
    return headers

def check_and_claim_daily(cfg, state):
    checkin_info = state.get("checkIn", {})
    if not checkin_info.get("claimedToday", False):
        log("Daily check-in belum diklaim hari ini. Mengklaim daily reward...")
        url = "https://server.victors.company/api/checkin"
        headers = build_headers(cfg)
        try:
            res = requests.post(url, headers=headers, json={}, timeout=15)
            if res.status_code == 200:
                log(f">> BERHASIL KLAIM DAILY CHECK-IN! Streak: {checkin_info.get('streak', 0) + 1} <<")
            else:
                log(f">> Check-in status: {res.status_code} - {res.text} <<")
        except Exception as e:
            log(f">> Gagal klaim daily check-in: {e} <<")

def check_and_claim_tasks(cfg):
    headers = build_headers(cfg)
    try:
        url = "https://server.victors.company/api/tasks"
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            tasks_data = res.json().get("tasks", [])
            for task in tasks_data:
                task_id = str(task.get("taskId", "")).strip()
                kind = str(task.get("kind", "")).strip()
                status = str(task.get("status", "")).strip()
                title = task.get("title", task_id)
                reward = task.get("reward", 0)

                # Abaikan hold tasks sesuai permintaan user (kecuali hold task)
                if "hold" in task_id.lower() or "hold" in kind.lower():
                    continue

                # Klaim jika task berstatus 'open'
                if status == "open":
                    log(f"Mencoba klaim task: '{title}' (ID: {task_id}, Reward: +{reward} VIC)...")
                    claim_url = "https://server.victors.company/api/tasks/claim"
                    c_res = requests.post(claim_url, headers=headers, json={"taskId": task_id}, timeout=15)
                    if c_res.status_code == 200:
                        c_data = c_res.json()
                        if c_data.get("success"):
                            log(f">> BERHASIL KLAIM TASK '{title}'! +{reward} VIC <<")
                        else:
                            log(f">> Gagal klaim task '{title}': {c_data.get('error', c_data)} <<")
                    else:
                        log(f">> Gagal klaim task '{title}' (Status {c_res.status_code}): {c_res.text} <<")
                    time.sleep(1.5)
        elif res.status_code in (401, 403):
            pass
        else:
            log(f">> Gagal mengambil daftar task ({res.status_code}): {res.text} <<")
    except Exception as e:
        log(f">> Error saat memproses tasks: {e} <<")

    # Auto-claim referral bonus dan komisi jika ada
    try:
        b_res = requests.post("https://server.victors.company/api/referral/claim-bonus", headers=headers, json={}, timeout=10)
        if b_res.status_code == 200 and b_res.json().get("success"):
            claimed_b = b_res.json().get("claimed", 0)
            if claimed_b > 0:
                log(f">> BERHASIL KLAIM REFERRAL BONUS: +{claimed_b} VIC <<")
    except Exception:
        pass

    try:
        c_res = requests.post("https://server.victors.company/api/referral/claim-commission", headers=headers, json={}, timeout=10)
        if c_res.status_code == 200 and c_res.json().get("success"):
            claimed_c = c_res.json().get("claimed", 0)
            if claimed_c > 0:
                log(f">> BERHASIL KLAIM REFERRAL COMMISSION: +{claimed_c} VIC <<")
    except Exception:
        pass

def claim_mining(cfg, can_retry=True):
    url = "https://server.victors.company/api/mining/claim"
    headers = build_headers(cfg)

    try:
        log("Mengirim request claim ke Victor's Company...")
        res = requests.post(url, headers=headers, json={}, timeout=20)
        status = res.status_code

        try:
            data = res.json()
        except Exception:
            data = res.text

        if status == 200 and isinstance(data, dict) and data.get("success"):
            claimed = data.get("claimed", 0)
            state = data.get("state", {})
            user = state.get("user", {})
            mining = state.get("mining", {})
            checkin = state.get("checkIn", {})
            config = state.get("config", {})

            balance = user.get("inAppBalance", 0)
            speed = mining.get("speed", 0)
            daily = mining.get("dailyOutput", 0)
            level = mining.get("level", 0)
            price = config.get("priceUsd", 0)
            usd_val = balance * price

            log("=" * 50)
            log(">> KLAIM BERHASIL! <<")
            log(f"Reward Diklaim : +{claimed:.4f} VIC")
            log(f"Total Saldo    : {balance:.2f} VIC (~${usd_val:.2f} USD)")
            log(f"Mining Level   : Lvl {level} (Speed: {speed}/hr | {daily}/day)")
            log(f"Daily Check-in : Streak {checkin.get('streak', 0)} hari (Sudah klaim: {checkin.get('claimedToday', False)})")
            log("=" * 50)

            # Auto claim daily check-in jika belum
            check_and_claim_daily(cfg, state)

            # Auto claim daily & community tasks (kecuali hold task)
            check_and_claim_tasks(cfg)
            return True, data

        elif status in (401, 403):
            if isinstance(data, dict) and data.get("code") == "HUMAN_REQUIRED":
                log(">> PERINGATAN: 'x-human-pass' kadaluarsa (HUMAN_REQUIRED). Menunggu input token baru dari Telegram bot (/setpass atau menu Detail Victor)... <<")
            else:
                log(f">> Autentikasi ditolak ({status}): {data} <<")
            return False, data

        elif status in (400, 429):
            log(f">> Cooldown aktif atau mining masih berjalan ({status}). Response: {data} <<")
            if isinstance(data, dict) and "state" in data:
                check_and_claim_daily(cfg, data["state"])
            check_and_claim_tasks(cfg)
            return True, data

        else:
            log(f">> Response status tidak terduga ({status}): {data} <<")
            return False, data

    except requests.exceptions.RequestException as e:
        log(f">> Request network error: {e} <<")
        return False, str(e)

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== Victor's Company Auto-Farmer Started ===")
    
    if once:
        claim_mining(cfg)
        return

    # Range klaim 60 menit s/d 90 menit (1h - 1:30h)
    min_min = cfg.get("min_interval_minutes", 60)
    max_min = cfg.get("max_interval_minutes", 90)

    while True:
        try:
            cfg = load_config()
        except Exception:
            pass
        
        ok, res_data = claim_mining(cfg)
        
        if not ok:
            # Jika klaim gagal sementara atau butuh token baru, periksa config.json setiap 2 detik
            retry_sleep = 60
            next_retry = datetime.datetime.now() + datetime.timedelta(seconds=retry_sleep)
            log(f"Klaim belum berhasil (menunggu pass baru/server ready), mencoba lagi dalam {retry_sleep} detik (pada {next_retry.strftime('%H:%M:%S')})...")
            last_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
            slept = 0
            while slept < retry_sleep:
                time.sleep(2)
                slept += 2
                try:
                    curr_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
                    if curr_mtime != last_mtime:
                        log("⚡ Perubahan config.json / x-human-pass terdeteksi! Membangunkan farmer segera...")
                        break
                except Exception:
                    pass
            continue

        # Random interval antara min_min dan max_min setelah klaim sukses
        sleep_minutes = random.randint(min_min, max_min)
        jitter_seconds = random.randint(10, 59)
        total_sleep = (sleep_minutes * 60) + jitter_seconds
        
        next_run = datetime.datetime.now() + datetime.timedelta(seconds=total_sleep)
        log(f"Tidur selama {sleep_minutes} menit {jitter_seconds} detik. Klaim berikutnya pada: {next_run.strftime('%H:%M:%S')}")
        
        # Tidur secara adaptif; bangun segera jika config.json diperbarui oleh Telegram bot
        last_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
        slept = 0
        while slept < total_sleep:
            step = min(5, total_sleep - slept)
            time.sleep(step)
            slept += step
            try:
                curr_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
                if curr_mtime != last_mtime:
                    log("⚡ Perubahan config.json / x-human-pass terdeteksi! Membangunkan farmer segera...")
                    break
            except Exception:
                pass

if __name__ == "__main__":
    main()
