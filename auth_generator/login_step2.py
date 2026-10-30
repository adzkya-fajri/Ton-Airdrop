#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(BASE_DIR, "tg_session")
STATE_FILE = os.path.join(BASE_DIR, "login_state.json")

async def main():
    if len(sys.argv) < 2:
        print("Penggunaan: python login_step2.py <OTP_CODE> [PASSWORD_2FA]")
        sys.exit(1)

    code = sys.argv[1].strip()
    password = sys.argv[2].strip() if len(sys.argv) > 2 else None

    if not os.path.exists(STATE_FILE):
        print("ERROR: login_state.json tidak ditemukan. Jalankan step1 terlebih dahulu!")
        sys.exit(1)

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    phone = state["phone"]
    phone_code_hash = state["phone_code_hash"]
    api_id = state["api_id"]
    api_hash = state["api_hash"]

    client = TelegramClient(SESSION_FILE, api_id, api_hash)
    await client.connect()

    try:
        try:
            user = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            print(f"LOGIN_SUCCESS: {user.first_name} {user.last_name or ''} (@{user.username or ''})")
        except SessionPasswordNeededError:
            if not password:
                print("2FA_PASSWORD_REQUIRED")
                return
            user = await client.sign_in(password=password)
            print(f"LOGIN_SUCCESS_2FA: {user.first_name} {user.last_name or ''} (@{user.username or ''})")

        me = await client.get_me()
        print(f"AKUN_TERHUBUNG: {me.id} | {me.first_name} (@{me.username})")

    except Exception as e:
        print(f"LOGIN_ERROR: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
