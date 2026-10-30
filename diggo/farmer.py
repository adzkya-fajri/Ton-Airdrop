import json
import os
import sys
import time
import random
import uuid
import datetime
import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farmer.log")
BASE_URL = "https://app.diggocoin.com"

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

def get_headers(cfg, need_idempotency=False):
    token = cfg.get("token", "").strip().replace("Bearer ", "")
    headers = {
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"),
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if need_idempotency:
        headers["Idempotency-Key"] = str(uuid.uuid4())
    return headers

def get_state(cfg):
    url = f"{BASE_URL}/api/state"
    headers = get_headers(cfg)
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("state", {})
        elif res.status_code == 401:
            log(">> ERROR: Bearer token Diggo expired / invalid! Perlu update token di config.json <<")
            return None
        else:
            log(f">> Gagal mengambil state ({res.status_code}): {res.text[:120]} <<")
            return None
    except Exception as e:
        log(f">> Exception saat get_state: {e} <<")
        return None

def check_and_claim_mining(cfg, state):
    if not state:
        return False

    mining = state.get("mining", {})
    server_now = state.get("serverNow", int(time.time() * 1000))
    next_claim_at = mining.get("stopsAt") or mining.get("nextClaimAt") or 0
    pending = mining.get("pending", 0)

    # Format waktu berikutnya
    dt_next = datetime.datetime.fromtimestamp(next_claim_at / 1000) if next_claim_at else None
    dt_str = dt_next.strftime("%Y-%m-%d %H:%M:%S") if dt_next else "Unknown"

    if server_now < next_claim_at:
        remaining_sec = max(0, int((next_claim_at - server_now) / 1000))
        rem_h = remaining_sec // 3600
        rem_m = (remaining_sec % 3600) // 60
        log(f"[Mining Cooldown] Siklus 8 jam belum selesai. Sisa waktu: {rem_h}j {rem_m}m (Klaim: {dt_str}). Pending: {pending:.4f} DIGGO")
        return False

    log(f"Waktu klaim tiba! Menjalankan klaim mining reward (+{pending:.4f} DIGGO)...")
    url = f"{BASE_URL}/api/claims/mining"
    headers = get_headers(cfg, need_idempotency=True)

    try:
        res = requests.post(url, headers=headers, json={}, timeout=15)
        data = res.json()
        if res.status_code == 200 and data.get("state"):
            new_state = data.get("state", {})
            new_balance = new_state.get("balance", 0)
            log("=" * 50)
            log(">> KLAIM DIGGO MINING BERHASIL! <<")
            log(f"Total Saldo Baru : {new_balance:.4f} DIGGO")
            log(f"Level Saat Ini   : Lvl {new_state.get('currentLevel', 0)}")
            log("=" * 50)
            return True
        elif res.status_code == 429 and data.get("error") == "mining_cooldown":
            log(f">> Server melaporkan masih dalam cooldown: {data} <<")
            return False
        else:
            log(f">> Respon klaim mining ({res.status_code}): {data} <<")
            return False
    except Exception as e:
        log(f">> Exception saat klaim mining Diggo: {e} <<")
        return False

def watch_and_claim_ad(cfg, task_data):
    log("Mendeteksi tugas menonton iklan Diggo ('ad'). Memulai siklus auto-ad...")
    headers = get_headers(cfg, need_idempotency=True)
    try:
        # 1. Start Adsgram attempt (body kosong sesuai schema backend Diggo)
        start_url = f"{BASE_URL}/api/adsgram/start"
        res = requests.post(start_url, headers=headers, json={}, timeout=15)
        if res.status_code != 200:
            log(f">> Gagal memulai ad Diggo ({res.status_code}): {res.text[:100]} <<")
            return False

        data = res.json() if isinstance(res.json(), dict) else {}
        attempt_id = data.get("attemptId")
        if data.get("ready"):
            log("Ad sudah ready! Mengklaim reward ad langsung...")
        elif attempt_id:
            log(f"Iklan Adsgram dimulai (Attempt: {attempt_id[:16]}...). Menunggu durasi video 15 detik...")
            time.sleep(15)

            # 2. Complete Adsgram attempt
            comp_url = f"{BASE_URL}/api/adsgram/complete"
            headers_comp = get_headers(cfg, need_idempotency=True)
            c_res = requests.post(comp_url, headers=headers_comp, json={"attemptId": attempt_id}, timeout=15)
            if c_res.status_code != 200:
                log(f">> Gagal menyelesaikan ad Diggo ({c_res.status_code}): {c_res.text[:100]} <<")
                return False
            log("Iklan Adsgram berhasil diselesaikan!")
            time.sleep(1)
        else:
            return False

        # 3. Claim ad task
        claim_url = f"{BASE_URL}/api/tasks/claim"
        headers_claim = get_headers(cfg, need_idempotency=True)
        claim_res = requests.post(claim_url, headers=headers_claim, json={"taskId": "ad"}, timeout=15)
        if claim_res.status_code == 200:
            log(">> BERHASIL KLAIM REWARD NONTON IKLAN DIGGO! <<")
            return True
        else:
            log(f">> Status reward task ad ({claim_res.status_code}): {claim_res.text[:100]} <<")
            return False
    except Exception as e:
        log(f">> Exception saat auto-watch ad Diggo: {e} <<")
        return False

def check_and_claim_tasks(cfg, state):
    if not state:
        return
    tasks = state.get("tasks", {})
    server_now = state.get("serverNow", int(time.time() * 1000))

    if not isinstance(tasks, dict):
        return

    for task_id, task_data in tasks.items():
        if not isinstance(task_data, dict):
            continue

        # Abaikan hold tasks sesuai permintaan
        if "hold" in str(task_id).lower():
            continue

        claimed = task_data.get("claimed", False)
        repeatable = task_data.get("repeatable", False)
        next_claim = task_data.get("nextClaimAt", 0)

        can_claim = False
        if not claimed:
            can_claim = True
        elif repeatable and server_now >= next_claim:
            can_claim = True

        if can_claim:
            if str(task_id).lower() == "ad":
                watch_and_claim_ad(cfg, task_data)
                continue

            log(f"Mencoba klaim task Diggo '{task_id}'...")
            url = f"{BASE_URL}/api/tasks/claim"
            headers = get_headers(cfg, need_idempotency=True)
            try:
                r = requests.post(url, headers=headers, json={"taskId": task_id}, timeout=15)
                data = r.json() if r.status_code == 200 else {}
                if r.status_code == 200 and data.get("success", True):
                    log(f">> BERHASIL KLAIM TASK DIGGO '{task_id}'! <<")
                else:
                    log(f">> Status task Diggo '{task_id}' ({r.status_code}): {r.text[:100]} <<")
            except Exception as e:
                log(f">> Gagal klaim task Diggo '{task_id}': {e} <<")
            time.sleep(1)

    # Auto-claim daily streak jika ada
    streak = state.get("streak")
    if isinstance(streak, dict) and not streak.get("claimedToday", False):
        day = streak.get("currentDay") or streak.get("day", 1)
        url = f"{BASE_URL}/api/streak/claim"
        headers = get_headers(cfg, need_idempotency=True)
        try:
            r = requests.post(url, headers=headers, json={"day": day}, timeout=15)
            if r.status_code == 200:
                log(f">> BERHASIL KLAIM DAILY STREAK DIGGO (Hari ke-{day})! <<")
        except Exception:
            pass

def check_and_claim_chest(cfg, state=None):
    url = f"{BASE_URL}/api/chests"
    headers = get_headers(cfg)
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return False
        data = res.json().get("chests", {})
        server_now = data.get("serverNow", int(time.time() * 1000))
        chests = data.get("chests", [])
        
        unlocked_chests = [c for c in chests if c.get("unlocked")]
        if not unlocked_chests:
            log("[Chest] Belum ada peti (chest) yang terbuka (unlocked).")
            return False
            
        unlocked_chests.sort(key=lambda x: x.get("level", 0), reverse=True)
        
        for chest in unlocked_chests:
            chest_id = chest.get("id")
            next_open = chest.get("nextOpenAt") or 0
            
            if server_now < next_open:
                rem_sec = max(0, int((next_open - server_now) / 1000))
                rem_h = rem_sec // 3600
                rem_m = (rem_sec % 3600) // 60
                log(f"[Chest Cooldown] Peti Diggo '{chest_id}' belum siap. Sisa waktu: {rem_h}j {rem_m}m")
                continue
                
            log(f"Peti Diggo '{chest_id}' siap dibuka! Menjalankan klaim chest...")
            open_url = f"{BASE_URL}/api/chests/open"
            open_headers = get_headers(cfg, need_idempotency=True)
            payload = {"chestId": chest_id, "mode": "live"}
            
            r_open = requests.post(open_url, headers=open_headers, json=payload, timeout=15)
            if r_open.status_code == 200:
                res_data = r_open.json()
                opening = res_data.get("opening", {})
                reward = opening.get("reward", {})
                new_state = res_data.get("state", {})
                new_bal = new_state.get("balance", 0)
                rew_asset = reward.get("asset", "DIGGO")
                rew_amt = reward.get("amount") or (reward.get("amountUnits", 0) / 1000000.0)
                rew_rarity = reward.get("rarity", "common")
                
                log("=" * 50)
                log(">> KLAIM DIGGO CHEST BERHASIL! <<")
                log(f"Peti             : {chest_id.title()}")
                log(f"Reward           : +{rew_amt} {rew_asset} ({rew_rarity})")
                log(f"Total Saldo Baru : {new_bal:.4f} DIGGO")
                log("=" * 50)
                return True
            elif r_open.status_code == 503 and "chest_reserve_insufficient" in r_open.text:
                log(f"[Chest Pool Kosong] Peti Diggo '{chest_id}' siap dibuka, tetapi reserve pool server Diggo saat ini belum didanai (unfunded). Bot akan otomatis klaim begitu pool tersedia.")
            else:
                log(f">> Respon buka chest '{chest_id}' ({r_open.status_code}): {r_open.text[:120]} <<")
                
        return False
    except Exception as e:
        log(f">> Exception saat check_and_claim_chest Diggo: {e} <<")
        return False

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== Diggo Miner Auto-Farmer Started ===")

    state = get_state(cfg)
    if state:
        player = state.get("player", {})
        balance = state.get("balance", 0)
        lvl = state.get("currentLevel", 0)
        log("=" * 50)
        log(f"Player      : {player.get('name', 'Diggo Player')} (ID: {player.get('id')})")
        log(f"Saldo Utama : {balance:.4f} DIGGO")
        log(f"Level Mining: Lvl {lvl}")
        log("=" * 50)
    else:
        log("Tidak dapat memuat state akun. Periksa token Anda.")

    if once:
        log("Mode: One-Shot Manual Test")
        check_and_claim_mining(cfg, state)
        check_and_claim_tasks(cfg, state)
        check_and_claim_chest(cfg, state)
        return

    while True:
        try:
            cfg = load_config()
            state = get_state(cfg)
            if state:
                check_and_claim_mining(cfg, state)
                check_and_claim_tasks(cfg, state)
                check_and_claim_chest(cfg, state)

                check_interval = cfg.get("check_interval_seconds", 900)
                jitter = random.randint(15, 60)
                sleep_time = check_interval + jitter
                log(f"Tidur selama {sleep_time} detik (~{sleep_time // 60} menit)...")
                
                # Adaptive sleep: cek mtime config.json tiap 3 detik
                last_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
                slept = 0
                while slept < sleep_time:
                    step = min(3, sleep_time - slept)
                    time.sleep(step)
                    slept += step
                    try:
                        curr_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
                        if curr_mtime != last_mtime:
                            log("⚡ Perubahan config.json / token Diggo terdeteksi! Membangunkan farmer segera...")
                            break
                    except Exception:
                        pass
            else:
                retry_sleep = 60
                log(f"Gagal memuat state (Token expired/server error). Menunggu token baru - cek ulang dalam {retry_sleep} detik...")
                last_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
                slept = 0
                while slept < retry_sleep:
                    time.sleep(2)
                    slept += 2
                    try:
                        curr_mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else 0
                        if curr_mtime != last_mtime:
                            log("⚡ Perubahan config.json / token Diggo terdeteksi! Membangunkan farmer segera...")
                            break
                    except Exception:
                        pass

        except KeyboardInterrupt:
            log("Farmer dihentikan.")
            break
        except Exception as e:
            log(f"Unexpected loop exception: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
