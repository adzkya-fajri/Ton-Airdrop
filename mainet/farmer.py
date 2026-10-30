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
BASE_URL = "https://api.mainet.io"

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

def solve_chq(val):
    try:
        raw = bytes.fromhex(val)
        xored = bytes([b ^ 157 for b in raw])
        js_code = xored.decode('utf-8', errors='ignore')
        
        # Eksekusi challenge JS dengan mock DOM browser di Node.js
        node_script = f"""
        const elements = {{}};
        const document = {{
          getElementById: (id) => {{
            if (!elements[id]) {{
              elements[id] = {{
                getAttribute: (k) => null,
                set innerHTML(html) {{
                  const regex = /id="([^"]+)"\\s+_d_="([^"]+)"/g;
                  let m;
                  while ((m = regex.exec(html)) !== null) {{
                    const elId = m[1];
                    const dVal = m[2];
                    elements[elId] = {{ getAttribute: (attr) => (attr === "_d_" ? dVal : null) }};
                  }}
                }}
              }};
            }}
            return elements[id];
          }}
        }};
        const code = {json.dumps(js_code)};
        const res = eval(code);
        console.log(res);
        """
        res = subprocess.run(['node', '-e', node_script], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        else:
            log(f">> Node execution error: {res.stderr.strip()} <<")
    except Exception as e:
        log(f">> Exception saat memecahkan CHQ challenge: {e} <<")
    return None

def login_with_init_data(cfg):
    init_data = cfg.get("init_data", "").strip()
    if not init_data:
        log(">> init_data belum diisi di config.json <<")
        return False, "init_data missing"

    url = f"{BASE_URL}/api/account/login"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "https://web.mainet.io",
        "Referer": "https://web.mainet.io/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"),
        "x-app": cfg.get("x_app", "mainet_server"),
        "x-cv": cfg.get("x_cv", "13")
    }

    payload = {
        "init_data": init_data,
        "referrer": ""
    }

    try:
        log("Mencoba auto-login mAInet via /api/account/login...")
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code not in (200, 201):
            log(f">> Gagal login tahap 1 mAInet ({res.status_code}): {res.text[:150]} <<")
            return False, res.text

        data = res.json()
        if "chq" in data and data["chq"]:
            chq = data["chq"]
            log("Menerima challenge CHQ anti-bot, menyelesaikan cipher DOM...")
            chr_val = solve_chq(chq)
            if chr_val is None:
                log(">> Gagal menyelesaikan challenge CHQ <<")
                return False, "Failed CHQ solve"

            payload["chr"] = int(chr_val) if chr_val.isdigit() else chr_val
            log(f"Mengirim hasil challenge: {payload['chr']}")
            res2 = requests.post(url, headers=headers, json=payload, timeout=15)
            if res2.status_code not in (200, 201):
                log(f">> Gagal login tahap 2 mAInet ({res2.status_code}): {res2.text[:150]} <<")
                return False, res2.text
            data = res2.json()

        access_token = data.get("access_token")
        if access_token:
            cfg["token"] = f"Bearer {access_token}"
            with open(CONFIG_PATH, "w") as f:
                json.dump(cfg, f, indent=4)
            log(">> AUTO-LOGIN MAINET BERHASIL! Token JWT baru berhasil disimpan <<")
            return True, access_token
        else:
            log(f">> Login response tidak memiliki access_token: {data} <<")
            return False, "No access_token"

    except Exception as e:
        log(f">> Exception saat auto-login mAInet: {e} <<")
        return False, str(e)

def get_headers(cfg):
    token = cfg.get("token", "").strip()
    if not token.startswith("Bearer "):
        token = f"Bearer {token}"
    return {
        "Accept": "*/*",
        "Authorization": token,
        "Content-Type": "application/json",
        "Origin": "https://web.mainet.io",
        "Referer": "https://web.mainet.io/",
        "User-Agent": cfg.get("user_agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"),
        "x-app": cfg.get("x_app", "mainet_server"),
        "x-cv": cfg.get("x_cv", "13")
    }

def collect_rewards(cfg, retried=False):
    url = f"{BASE_URL}/api/player/collectReward"
    headers = get_headers(cfg)

    try:
        log("Mengeksekusi klaim mining reward di mAInet...")
        res = requests.post(url, headers=headers, json={}, timeout=15)
        
        if res.status_code in (200, 201):
            data = res.json()
            player = data.get("player", {})
            nickname = player.get("nickname", "Player")
            shares = player.get("shares", 0)
            power = player.get("total_power", 0)
            asics = player.get("asics", [])
            asic_lvl = asics[0].get("level", 0) if asics else 0
            need_captcha = player.get("need_captcha", False)

            log("=" * 50)
            log(">> KLAIM MAINET BERHASIL! <<")
            log(f"Player      : {nickname} (ID: {player.get('id')})")
            log(f"Total Shares: {shares:,.2f}")
            log(f"ASIC Power  : {power} TH/s (ASIC Lvl {asic_lvl})")
            log(f"Need Captcha: {need_captcha}")
            log("=" * 50)
            return True, data

        elif res.status_code == 401:
            log(">> ERROR 401: Token Bearer mAInet kadaluarsa! <<")
            if not retried and cfg.get("init_data"):
                log("Mencoba auto-refresh token menggunakan init_data...")
                ok, _ = login_with_init_data(cfg)
                if ok:
                    # Muat ulang config baru dengan token segar
                    new_cfg = load_config()
                    return collect_rewards(new_cfg, retried=True)
            return False, res.text

        else:
            log(f">> Respon klaim mAInet ({res.status_code}): {res.text[:150]} <<")
            return False, res.text

    except Exception as e:
        log(f">> Exception saat klaim mAInet: {e} <<")
        return False, str(e)

def get_next_delay(cfg):
    min_m = cfg.get("min_interval_minutes", 45)
    max_m = cfg.get("max_interval_minutes", 60)
    minutes = random.randint(min_m, max_m)
    seconds = random.randint(10, 59)
    return (minutes * 60) + seconds

def main():
    cfg = load_config()
    once = "--once" in sys.argv

    log("=== mAInet Auto-Farmer Started ===")

    if once:
        log("Mode: One-Shot Manual Test")
        collect_rewards(cfg)
        return

    while True:
        try:
            success, _ = collect_rewards(cfg)

            delay_seconds = get_next_delay(cfg)
            next_run = datetime.datetime.now() + datetime.timedelta(seconds=delay_seconds)
            log(f"Tidur ~{delay_seconds//60} menit. Klaim berikutnya pada: {next_run.strftime('%H:%M:%S')}")
            time.sleep(delay_seconds)

        except KeyboardInterrupt:
            log("Farmer dihentikan oleh user.")
            break
        except Exception as e:
            log(f"Unexpected loop exception: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
