import json
import os
import sys
import time
import random
import datetime
import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmer.log")
BASE_URL = "https://mrg.up.railway.app"

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
    return {
        "Origin": "https://app.mrgtoken.xyz",
        "Referer": "https://app.mrgtoken.xyz/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Content-Type": "application/json",
        "Accept": "*/*"
    }

def ping_server(cfg):
    url = f"{BASE_URL}/api/user/ping"
    headers = get_headers(cfg)
    try:
        res = requests.post(url, headers=headers, json={"initData": cfg["init_data"]}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                log(f"[Ping] Online! Active users in MRG network: {data.get('activeNow', 0)}")
                return True
        return False
    except Exception as e:
        log(f"[Ping] Network error: {e}")
        return False

def check_daily_checkin(cfg):
    url = f"{BASE_URL}/api/user/daily-checkin"
    headers = get_headers(cfg)
    try:
        res = requests.post(url, headers=headers, json={"initData": cfg["init_data"]}, timeout=15)
        data = res.json()
        if res.status_code == 200 and data.get("success"):
            log(f">> BERHASIL KLAIM DAILY CHECK-IN! Streak: {data.get('user', {}).get('checkinStreak', 0)} hari <<")
        elif res.status_code == 400 and "already checked in" in data.get("error", "").lower():
            pass # Sudah klaim hari ini, normal
        else:
            log(f"[Check-in] Status: {res.status_code} - {data}")
    except Exception as e:
        log(f"[Check-in] Error: {e}")

def check_and_claim_tasks(cfg):
    url = f"{BASE_URL}/api/user/me"
    headers = get_headers(cfg)
    try:
        res = requests.post(url, headers=headers, json={"initData": cfg["init_data"]}, timeout=15)
        if res.status_code == 200:
            tasks = res.json().get("tasks", [])
            for t in tasks:
                tid = str(t.get("taskId", "")).strip()
                title = str(t.get("title", tid)).strip()
                reward = t.get("reward", 0)

                # Abaikan hold tasks sesuai instruksi
                if "hold" in tid.lower() or "hold" in title.lower():
                    continue

                # 1. Kirim task-click
                try:
                    requests.post(f"{BASE_URL}/api/user/task-click", headers=headers, json={"initData": cfg["init_data"], "taskId": tid}, timeout=10)
                except Exception:
                    pass
                time.sleep(1)

                # 2. Kirim claim-task
                try:
                    c_res = requests.post(f"{BASE_URL}/api/user/claim-task", headers=headers, json={"initData": cfg["init_data"], "taskId": tid}, timeout=10)
                    if c_res.status_code == 200 and c_res.json().get("success"):
                        log(f">> BERHASIL KLAIM TASK MRG '{title}'! +{reward} MRG <<")
                except Exception:
                    pass
    except Exception as e:
        log(f">> Error saat memproses tasks MRG: {e} <<")

    # Auto-claim referral bonus dan komisi jika ada
    try:
        b_res = requests.post(f"{BASE_URL}/api/user/claim-one-time-bonus", headers=headers, json={"initData": cfg["init_data"]}, timeout=10)
        if b_res.status_code == 200 and b_res.json().get("success"):
            claimed = b_res.json().get("claimedAmount", 0)
            if claimed:
                log(f">> BERHASIL KLAIM REFERRAL BONUS MRG: +{claimed} MRG <<")
    except Exception:
        pass

    try:
        c_res = requests.post(f"{BASE_URL}/api/user/claim-commission", headers=headers, json={"initData": cfg["init_data"]}, timeout=10)
        if c_res.status_code == 200 and c_res.json().get("success"):
            claimed = c_res.json().get("claimedAmount", 0)
            if claimed:
                log(f">> BERHASIL KLAIM KOMISI REFERRAL MRG: +{claimed} MRG <<")
    except Exception:
        pass

def claim_mining(cfg):
    url = f"{BASE_URL}/api/user/claim-mining"
    headers = get_headers(cfg)
    try:
        log("Mengeksekusi klaim mining reward di MRG...")
        res = requests.post(url, headers=headers, json={"initData": cfg["init_data"]}, timeout=15)
        data = res.json()
        if res.status_code == 200 and data.get("success"):
            claimed = data.get("claimedAmount", "0")
            user = data.get("user", {})
            balance = user.get("inAppBalance", 0)
            level = user.get("miningSnapshot", {}).get("level", 0)
            streak = user.get("checkinStreak", 0)

            log("=" * 50)
            log(">> KLAIM MRG BERHASIL! <<")
            log(f"Reward Diklaim : +{claimed} MRG")
            log(f"Total Saldo    : {balance:.4f} MRG")
            log(f"Mining Level   : Lvl {level}")
            log(f"Daily Check-in : Streak {streak} hari")
            log("=" * 50)

            check_daily_checkin(cfg)
            check_and_claim_tasks(cfg)
            return True, data
        elif res.status_code == 400 and "no mining balance" in data.get("error", "").lower():
            log(f">> Mining balance masih kosong atau baru saja diklaim. <<")
            check_daily_checkin(cfg)
            check_and_claim_tasks(cfg)
            return False, data
        elif res.status_code == 403 and data.get("code") == "HUMAN_CHECK_REQUIRED":
            log(f"⚠️ [MRG Human Check Required] Klaim reward ditahan: Server mewajibkan 1x Security Check di Telegram Mini-App (@mrgminerbot).")
            # Cek saldo saat ini dari user/me
            try:
                me_res = requests.post(f"{BASE_URL}/api/user/me", headers=headers, json={"initData": cfg["init_data"]}, timeout=10)
                if me_res.status_code == 200:
                    u = me_res.json().get("user", {})
                    unclaimed = u.get("unclaimedMiningBalance", 0)
                    bal = u.get("inAppBalance", 0)
                    lvl = me_res.json().get("activeLevel", 0)
                    log(f"   ℹ️ Status Mining Tetap Aktif! Saldo: {bal:.4f} MRG | Belum Diklaim: {unclaimed:.4f} MRG (Lvl {lvl})")
            except Exception:
                pass
            return False, data
        else:
            log(f">> Klaim MRG respon ({res.status_code}): {data} <<")
            return False, data
    except Exception as e:
        log(f">> Exception saat klaim MRG: {e} <<")
        return False, str(e)

def get_next_claim_delay(cfg):
    min_m = cfg.get("min_claim_interval_minutes", 60)
    max_m = cfg.get("max_claim_interval_minutes", 90)
    minutes = random.randint(min_m, max_m)
    seconds = random.randint(10, 59)
    return (minutes * 60) + seconds

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== MRG (Mine Rare Gram) Auto-Farmer Started ===")

    if once:
        log("Mode: One-Shot Manual Test")
        ping_server(cfg)
        claim_mining(cfg)
        check_daily_checkin(cfg)
        check_and_claim_tasks(cfg)
        return

    log("Inisialisasi startup: mengecek ping, mining, checkin & tasks...")
    last_ping_time = time.time()
    last_task_check_time = time.time()
    ping_server(cfg)
    claim_mining(cfg)
    check_daily_checkin(cfg)
    check_and_claim_tasks(cfg)

    claim_delay = get_next_claim_delay(cfg)
    next_claim_time = time.time() + claim_delay
    log(f"Klaim berkala diatur 60-90 menit. Klaim berikutnya pada: {datetime.datetime.fromtimestamp(next_claim_time).strftime('%H:%M:%S')}")

    while True:
        try:
            cfg = load_config()
            now = time.time()

            # Ping setiap 5 menit agar status akun selalu aktif di server
            if now - last_ping_time >= 300:
                ping_server(cfg)
                last_ping_time = now

            # Cek dan klaim tasks berkala setiap 20 menit (agar task segera terklaim setelah cooldown)
            if now - last_task_check_time >= 1200:
                check_and_claim_tasks(cfg)
                last_task_check_time = now

            # Waktunya claim mining reward
            if now >= next_claim_time:
                claim_mining(cfg)
                claim_delay = get_next_claim_delay(cfg)
                next_claim_time = time.time() + claim_delay
                log(f"Klaim berikutnya dijadwalkan pada: {datetime.datetime.fromtimestamp(next_claim_time).strftime('%H:%M:%S')}")

            time.sleep(30)

        except KeyboardInterrupt:
            log("Farmer dihentikan oleh user.")
            break
        except Exception as e:
            log(f"Unexpected loop exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
