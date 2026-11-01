#!/usr/bin/env python3
"""
Dead-Bot & Endpoint Health Detector for Telegram Farming Cluster (v2.0 Intelligent)
Audits HTTP endpoints, DNS resolutions, and recent farmer runtime telemetry across all bots.
Categorizes into:
  - HEALTHY: Running smoothly, API alive, recent claim success.
  - DEGRADED: Server 500/502/503 errors, high latency, or intermittent timeouts.
  - DEAD/SCAM: DNS NXDOMAIN, domain expired, endpoint removed, or paywall deposit scam.
Generates structured health report to farmers/dead_bots.json and cluster_status.json.
"""

import os
import sys
import json
import time
import socket
import urllib.parse
import argparse
from datetime import datetime

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    requests = None

FARMERS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(FARMERS_DIR, "REGISTRY.json")
REPORT_PATH = os.path.join(FARMERS_DIR, "dead_bots.json")
CLUSTER_STATUS_PATH = os.path.join(FARMERS_DIR, "cluster_status.json")

USER_AGENT = "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.107 Mobile Safari/537.36 Telegram-Android/11.2.2"

def resolve_dns(host):
    try:
        socket.gethostbyname(host)
        return True, "DNS OK"
    except socket.gaierror as e:
        return False, f"NXDOMAIN / Domain Not Found: {e}"
    except Exception as e:
        return False, f"DNS Error: {e}"

def check_recent_log_health(bot_id):
    """Check last 50 lines of farmer log to detect fatal errors, scam paywalls, or successful claims."""
    log_file = os.path.join(FARMERS_DIR, bot_id, "farmer.log")
    if not os.path.exists(log_file):
        return None, "No log file"

    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-60:]
        text = "".join(lines)

        # Deteksi indikator scam paywall / deposit required
        if "requiresVerification" in text or "0.05 TON transaction to activate" in text:
            return "DEAD_SCAM", "Paywall Scam (Meminta deposit TON untuk mining)"

        # Deteksi indikator klaim sukses
        success_keywords = ["KLAIM", "BERHASIL", "CLAIM SUCCESS", "Reward:", "Sukses", "Balance:", "Shares:", "Streak Day", "Siklus", "Sleeping"]
        if any(kw in text for kw in success_keywords):
            # Cek mtime
            mtime = os.path.getmtime(log_file)
            age_hours = (time.time() - mtime) / 3600
            if age_hours < 6:
                return "ACTIVE", f"Aktif farming ({age_hours:.1f}j lalu)"
            else:
                return "STALE", f"Log terakhir {age_hours:.1f}j lalu"

        return "UNKNOWN", "Log aktif"
    except Exception as e:
        return None, str(e)

def check_http_endpoint(url, bot_id):
    if not url or not url.startswith("http"):
        return "HEALTHY", "Telegram Native / Telethon MTProto (No HTTP API)", None

    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.split(":")[0]

    # 1. DNS Resolution Check
    dns_ok, dns_msg = resolve_dns(host)
    if not dns_ok:
        return "DEAD", dns_msg, None

    # 2. HTTP Request Check
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Connection": "close"
    }

    try:
        req = requests.get(url, headers=headers, timeout=8, allow_redirects=True, verify=False)
        code = req.status_code

        if code in (200, 201, 204):
            return "HEALTHY", f"HTTP {code} OK", code
        elif code in (400, 401, 403):
            return "HEALTHY", f"HTTP {code} Server Aktif (Auth/Payload Required)", code
        elif code == 404:
            # Jika root path /api memberi 404, uji origin web domainnya
            origin_url = f"{parsed.scheme}://{parsed.netloc}"
            if origin_url != url:
                try:
                    oreq = requests.get(origin_url, headers=headers, timeout=6, allow_redirects=True, verify=False)
                    if oreq.status_code in (200, 201, 204, 301, 302, 401, 403):
                        return "HEALTHY", f"HTTP 404 API Path, tapi Web Origin ({oreq.status_code}) Aktif", oreq.status_code
                except Exception:
                    pass

            # Cek apakah log farmer tetap aktif dan sukses
            log_st, log_msg = check_recent_log_health(bot_id)
            if log_st == "ACTIVE":
                return "HEALTHY", f"HTTP 404 GET Root, tapi Farmer Aktif ({log_msg})", code

            return "DEAD", "HTTP 404 Not Found (Endpoint Dicabut / Tidak Ditemukan)", code
        elif code in (500, 502, 503, 504):
            return "DEGRADED", f"HTTP {code} Server Mengalami Gangguan", code
        else:
            return "HEALTHY", f"HTTP {code}", code

    except requests.exceptions.SSLError as e:
        return "DEGRADED", f"SSL Certificate Error: {e}", None
    except requests.exceptions.ConnectionError as e:
        return "DEAD", f"Connection Refused / Server Mati: {e}", None
    except requests.exceptions.Timeout:
        return "DEGRADED", "Connection Timeout (>8 seconds)", None
    except Exception as e:
        return "DEGRADED", f"Network Error: {str(e)[:60]}", None

def run_deadbot_audit():
    if not os.path.exists(REGISTRY_PATH):
        print(f"[ERROR] REGISTRY.json not found di {REGISTRY_PATH}")
        return {}

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    bots = registry.get("bots", {})
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_audited": len(bots),
        "healthy_count": 0,
        "degraded_count": 0,
        "dead_count": 0,
        "dead_bots": [],
        "degraded_bots": [],
        "healthy_bots": []
    }

    print(f"[*] Menjalankan Audit Deteksi Bot Mati pada {len(bots)} bot...")

    for bot_id, info in bots.items():
        name = info.get("name", bot_id)
        bot_handle = info.get("bot", "")
        api_base = info.get("api_base") or info.get("webapp_url") or ""

        # 1. Cek kesehatan via log dan scam paywall
        log_st, log_msg = check_recent_log_health(bot_id)
        if log_st == "DEAD_SCAM":
            status = "DEAD"
            reason = log_msg
            http_code = None
        else:
            # 2. Cek kesehatan endpoint HTTP & DNS
            status, reason, http_code = check_http_endpoint(api_base, bot_id)

        bot_entry = {
            "id": bot_id,
            "name": name,
            "handle": bot_handle,
            "endpoint": api_base,
            "status": status,
            "reason": reason,
            "http_code": http_code
        }

        if status == "HEALTHY":
            results["healthy_count"] += 1
            results["healthy_bots"].append(bot_entry)
            print(f"  [+] {name} ({bot_id}): SEHAT ({reason})")
        elif status == "DEGRADED":
            results["degraded_count"] += 1
            results["degraded_bots"].append(bot_entry)
            print(f"  [!] {name} ({bot_id}): DEGRADED ({reason})")
        elif status == "DEAD":
            results["dead_count"] += 1
            results["dead_bots"].append(bot_entry)
            print(f"  [-] {name} ({bot_id}): MATI / SCAM ({reason})")

    # Daftar bot yang sudah diarsipkan sebelumnya
    deleted_bots_dir = os.path.join(FARMERS_DIR, ".deleted_bots")
    if os.path.exists(deleted_bots_dir):
        archived = [d for d in os.listdir(deleted_bots_dir) if os.path.isdir(os.path.join(deleted_bots_dir, d))]
        results["archived_dead_bots"] = archived
    else:
        results["archived_dead_bots"] = []

    # Simpan hasil audit
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[OK] Laporan audit berhasil disimpan ke {REPORT_PATH}")

    # Perbarui cluster_status.json
    cluster_status = {}
    if os.path.exists(CLUSTER_STATUS_PATH):
        try:
            with open(CLUSTER_STATUS_PATH, "r", encoding="utf-8") as f:
                cluster_status = json.load(f)
        except Exception:
            pass
    cluster_status["dead_bots_audit"] = {
        "last_checked": results["timestamp"],
        "healthy": results["healthy_count"],
        "degraded": results["degraded_count"],
        "dead": results["dead_count"]
    }
    with open(CLUSTER_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(cluster_status, f, indent=2)

    return results

def print_summary(report):
    print("\n" + "=" * 55)
    print(f" HASIL AUDIT DETEKSI BOT MATI ({report.get('timestamp')})")
    print("=" * 55)
    print(f" Total Bot Diaudit: {report.get('total_audited')} Bot")
    print(f" Kondisi Sehat    : {report.get('healthy_count')} Bot")
    print(f" Terdegradasi     : {report.get('degraded_count')} Bot")
    print(f" Mati / Scam      : {report.get('dead_count')} Bot")
    print("-" * 55)

    if report.get("dead_bots"):
        print(" [!] DAFTAR BOT MATI / BERMASALAH:")
        for b in report["dead_bots"]:
            print(f"   • {b['name']} ({b['id']}): {b['reason']}")
    else:
        print(" [OK] Tidak ada bot mati yang terdeteksi.")

    if report.get("degraded_bots"):
        print(" [!] DAFTAR BOT TERDEGRADASI (GANGGUAN SERVER):")
        for b in report["degraded_bots"]:
            print(f"   • {b['name']} ({b['id']}): {b['reason']}")

    if report.get("archived_dead_bots"):
        print(f" [~] Bot Terarsip di .deleted_bots: {', '.join(report['archived_dead_bots'])}")
    print("=" * 55)

def main():
    parser = argparse.ArgumentParser(description="Detektor Bot Mati & Kesehatan Endpoint Cluster")
    parser.add_argument("--audit", action="store_true", help="Jalankan audit lengkap")
    parser.add_argument("--json", action="store_true", help="Cetak hasil format JSON")
    parser.add_argument("--summary", action="store_true", help="Cetak ringkasan hasil audit terakhir")
    args = parser.parse_args()

    if args.summary:
        if os.path.exists(REPORT_PATH):
            with open(REPORT_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)
            print_summary(report)
        else:
            report = run_deadbot_audit()
            print_summary(report)
        return

    report = run_deadbot_audit()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_summary(report)

if __name__ == "__main__":
    main()
