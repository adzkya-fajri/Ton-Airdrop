#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from telethon import TelegramClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(BASE_DIR, "tg_session")
STATE_FILE = os.path.join(BASE_DIR, "login_state.json")

API_ID = 30234133
API_HASH = "142e316c8fce3f9a94b655a3d3593aee"
PHONE = "+6281998958020"

async def main():
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        print("ALREADY_AUTHORIZED")
        await client.disconnect()
        return

    print(f"Mengirim permintaan kode login ke nomor {PHONE}...")
    try:
        sent = await client.send_code_request(PHONE)
        state = {
            "phone": PHONE,
            "phone_code_hash": sent.phone_code_hash,
            "api_id": API_ID,
            "api_hash": API_HASH
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        print("CODE_SENT_SUCCESS")
        print(f"Tipe pengiriman kode: {type(sent.type).__name__}")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
