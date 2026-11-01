#!/usr/bin/env python3
"""
log_rotator.py - Pembersih & Log Rotator Otomatis untuk Seluruh Bot Pertanian Crypto
Aturan Pemangkasan:
- Batas Maksimum: 5 MB (5,242,880 bytes)
- Target Pemangkasan: 3 MB (3,145,728 bytes)
- Menjaga keutuhan baris (line boundary preserved)
- Penggantian atomik (POSIX os.replace) agar tidak mengganggu proses bot yang sedang aktif
"""

import os
import sys
import glob
import time
import argparse
import datetime
from typing import Dict, List, Any

# Direktori utama
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Konstanta Default
DEFAULT_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
DEFAULT_KEEP_BYTES = 3 * 1024 * 1024  # 3 MB

def format_size(bytes_val: int) -> str:
    """Format bytes ke satuan yang mudah dibaca (B, KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:3.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

def rotate_single_log(
    file_path: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    keep_bytes: int = DEFAULT_KEEP_BYTES,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Memeriksa dan memotong berkas log jika ukurannya melebihi max_bytes.
    Menyimpan keep_bytes terakhir dari berkas, sejajar dengan batas baris baru (newline).
    """
    result = {
        "path": file_path,
        "rel_path": os.path.relpath(file_path, BASE_DIR),
        "initial_size": 0,
        "final_size": 0,
        "freed_bytes": 0,
        "rotated": False,
        "error": None
    }

    try:
        if not os.path.isfile(file_path):
            return result

        size = os.path.getsize(file_path)
        result["initial_size"] = size
        result["final_size"] = size

        if size <= max_bytes:
            return result

        # Berkas melebihi max_bytes, perlu dipangkas ke keep_bytes
        result["rotated"] = True
        result["freed_bytes"] = size - keep_bytes

        if dry_run:
            result["final_size"] = keep_bytes
            return result

        # Buka file dalam mode binary untuk pemotongan presisi
        with open(file_path, "rb") as f:
            f.seek(size - keep_bytes)
            # Lewati potongan baris yang tidak lengkap sampai menemukan newline berikutnya
            f.readline()
            trimmed_content = f.read()

        # Buat header rotasi log
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"\n--- [LOG ROTATED BY LOG_ROTATOR at {timestamp_str} (Preserved latest 3 MB)] ---\n".encode("utf-8")
        full_content = header + trimmed_content

        # Tulis ke file temporary terlebih dahulu untuk menjamin atomisitas
        tmp_path = file_path + ".rot_tmp"
        with open(tmp_path, "wb") as f_tmp:
            f_tmp.write(full_content)

        # Ganti file lama secara atomik
        os.replace(tmp_path, file_path)

        new_size = os.path.getsize(file_path)
        result["final_size"] = new_size
        result["freed_bytes"] = size - new_size

    except Exception as e:
        result["error"] = str(e)
        # Bersihkan temporary jika masih ada
        tmp_path = file_path + ".rot_tmp"
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return result

def scan_log_files(root_dir: str = BASE_DIR) -> List[str]:
    """Memindai seluruh berkas *.log di bawah direktori root, mengabaikan venv dan .git."""
    log_files = []
    for root, dirs, files in os.walk(root_dir):
        # Abaikan direktori tersembunyi, venv, dan .git
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["venv", "node_modules", "__pycache__"]]
        for f in files:
            if f.endswith(".log"):
                log_files.append(os.path.join(root, f))
    return sorted(log_files)

def run_log_rotation(
    root_dir: str = BASE_DIR,
    max_bytes: int = DEFAULT_MAX_BYTES,
    keep_bytes: int = DEFAULT_KEEP_BYTES,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Menjalankan rotasi pada seluruh berkas log di direktori root.
    Mengembalikan statistik keseluruhan.
    """
    logs = scan_log_files(root_dir)
    results = []
    total_initial = 0
    total_final = 0
    total_freed = 0
    rotated_count = 0

    for path in logs:
        res = rotate_single_log(path, max_bytes=max_bytes, keep_bytes=keep_bytes, dry_run=dry_run)
        results.append(res)
        total_initial += res["initial_size"]
        total_final += res["final_size"]
        total_freed += res["freed_bytes"]
        if res["rotated"]:
            rotated_count += 1

    summary = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scanned_files": len(logs),
        "rotated_files": rotated_count,
        "total_initial_bytes": total_initial,
        "total_final_bytes": total_final,
        "total_freed_bytes": total_freed,
        "dry_run": dry_run,
        "details": results
    }
    return summary

def main():
    parser = argparse.ArgumentParser(description="Pembersih & Log Rotator Otomatis untuk Bot Pertanian Crypto")
    parser.add_argument("--dry-run", action="store_true", help="Simulasi pemindaian tanpa mengubah berkas fisik")
    parser.add_argument("--max-mb", type=float, default=5.0, help="Batas maksimal ukuran log dalam MB (default: 5.0 MB)")
    parser.add_argument("--keep-mb", type=float, default=3.0, help="Ukuran log yang dipertahankan setelah dipangkas dalam MB (default: 3.0 MB)")
    parser.add_argument("--all", action="store_true", help="Tampilkan detail semua log termasuk yang tidak dipangkas")
    
    args = parser.parse_args()

    max_b = int(args.max_mb * 1024 * 1024)
    keep_b = int(args.keep_mb * 1024 * 1024)

    mode_label = "[SIMULASI DRY-RUN]" if args.dry_run else "[EKSEKUSI ROTASI]"
    print("=" * 70)
    print(f"🪓 LOG ROTATOR OTOMATIS {mode_label}")
    print(f"Batas Maksimum : {args.max_mb} MB ({max_b} bytes)")
    print(f"Target Pangkas : {args.keep_mb} MB ({keep_b} bytes)")
    print(f"Direktori Basis: {BASE_DIR}")
    print("=" * 70)

    summary = run_log_rotation(root_dir=BASE_DIR, max_bytes=max_b, keep_bytes=keep_b, dry_run=args.dry_run)

    print(f"\n📂 Total berkas log dipindai: {summary['scanned_files']}")
    print(f"✂️ Berkas perlu dipangkas (> {args.max_mb} MB): {summary['rotated_files']}")
    print(f"💾 Total ukuran awal : {format_size(summary['total_initial_bytes'])}")
    print(f"📦 Total ukuran akhir: {format_size(summary['total_final_bytes'])}")
    print(f"🎉 Ruang disk dihemat: {format_size(summary['total_freed_bytes'])}\n")

    if summary['rotated_files'] > 0:
        print("--- DAFTAR BERKAS YANG DIPANGKAS ---")
        for d in summary['details']:
            if d['rotated']:
                print(f" • {d['rel_path']}: {format_size(d['initial_size'])} -> {format_size(d['final_size'])} (Hemat: {format_size(d['freed_bytes'])})")
    elif args.all:
        print("--- STATUS SEMUA BERKAS LOG ---")
        for d in summary['details']:
            print(f" • {d['rel_path']}: {format_size(d['initial_size'])}")
    else:
        print("✅ Semua berkas log saat ini masih berada di bawah batas 5 MB. Tidak ada pemangkasan yang diperlukan.")

    print("=" * 70)

if __name__ == "__main__":
    main()
