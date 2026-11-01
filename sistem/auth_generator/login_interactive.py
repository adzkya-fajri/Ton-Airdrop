#!/usr/bin/env python3
"""
login_interactive.py - Skrip Login Telegram Interaktif Mandiri
Dijalankan langsung oleh pengguna di terminal lokal untuk keamanan maksimal:
Kode OTP & Password 2FA diketik langsung di terminal lokal tanpa lewat chat AI.
"""

import os
import sys
import getpass
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(BASE_DIR, "tg_session")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
DEFAULT_PHONE = os.getenv("TELEGRAM_PHONE", "")

async def interactive_login():
    print("=" * 60)
    print("🔐 LOGIN TELEGRAM RESMI (TELETHON MTPROTO)")
    print("=" * 60)
    
    session_db = SESSION_FILE + ".session"
    if os.path.exists(session_db):
        try:
            client_test = TelegramClient(SESSION_FILE, API_ID, API_HASH)
            await client_test.connect()
            if await client_test.is_user_authorized():
                me = await client_test.get_me()
                print(f"\n✅ Sesi sudah terotorisasi untuk: {me.first_name} (@{me.username}) ID: {me.id}")
                await client_test.disconnect()
                return
            await client_test.disconnect()
            print("ℹ️ Menghapus berkas sesi lama yang telah diterminate agar membuat otorisasi baru yang bersih...")
            os.remove(session_db)
        except Exception as e:
            print(f"ℹ️ Reset berkas sesi lama: {e}")
            if os.path.exists(session_db):
                os.remove(session_db)

    phone = input(f"Masukkan nomor telepon [{DEFAULT_PHONE}]: ").strip()
    if not phone:
        phone = DEFAULT_PHONE
        
    print(f"\n📡 Menghubungkan ke server Telegram untuk nomor {phone}...")
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"\n✅ Sesi sudah terotorisasi untuk: {me.first_name} (@{me.username}) ID: {me.id}")
        await client.disconnect()
        return

    print("📲 Mengirimkan permintaan kode verifikasi resmi...")
    try:
        sent = await client.send_code_request(phone)
        print("✅ Kode berhasil dikirim! Silakan periksa aplikasi Telegram di HP Anda.")
    except Exception as e:
        print(f"❌ Gagal mengirim permintaan kode: {e}")
        await client.disconnect()
        return

    code = input("\n👉 Masukkan kode OTP Telegram yang Anda terima: ").strip()
    # Bersihkan spasi atau karakter non-digit jika ada
    code = code.replace(" ", "").replace("-", "")

    try:
        user = await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
        print(f"\n🎉 LOGIN SUKSES! Selamat datang, {user.first_name} (@{user.username})")
    except SessionPasswordNeededError:
        print("\n🔒 Akun Anda mengaktifkan Two-Step Verification (2FA).")
        pwd = getpass.getpass("👉 Masukkan kata sandi 2FA Anda: ")
        try:
            user = await client.sign_in(password=pwd)
            print(f"\n🎉 LOGIN 2FA SUKSES! Selamat datang, {user.first_name} (@{user.username})")
        except Exception as e:
            print(f"\n❌ Kata sandi 2FA salah atau gagal: {e}")
            await client.disconnect()
            return
    except Exception as e:
        print(f"\n❌ Login gagal: {e}")
        await client.disconnect()
        return

    me = await client.get_me()
    print("=" * 60)
    print(f"✅ Sesi tersimpan aman di: {SESSION_FILE}.session")
    print(f"👤 User ID : {me.id}")
    print(f"📛 Username: @{me.username}")
    print("=" * 60)
    print("💡 Anda sekarang bisa kembali ke chat AI untuk melanjutkan sinkronisasi bot.")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(interactive_login())
