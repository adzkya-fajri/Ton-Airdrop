#!/usr/bin/env python3
"""
Master Orchestrator Runner for Newly Audited Bots
Launches:
1. Supabase Edge Multi-Bot (@freeautousdt_bot, @dogsempirebot, @Ton_nMinersBot)
2. LiteBits Bitcoin Lightning Faucet (@Litebits_faucet_bot)
"""

import os
import sys
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_BIN = os.path.join(BASE_DIR, "auth_generator", "venv", "bin", "python")
if not os.path.exists(PYTHON_BIN):
    PYTHON_BIN = sys.executable

def run_once():
    print("=" * 60)
    print("  RUNNING SINGLE TEST CYCLE (--once)")
    print("=" * 60)
    
    # 1. Supabase Multi-Bot
    print("\n>>> Launching Supabase Multi-Bot Farmer...")
    supabase_script = os.path.join(BASE_DIR, "sistem", "supabase_miners", "farmer.py")
    if not os.path.exists(supabase_script):
        supabase_script = os.path.join(BASE_DIR, "supabase_miners", "farmer.py")
    subprocess.run([PYTHON_BIN, supabase_script, "--once"])
    
    # 2. LiteBits Faucet
    print("\n>>> Launching LiteBits Faucet Farmer...")
    litebits_script = os.path.join(BASE_DIR, "sistem", "litebits", "farmer.py")
    if not os.path.exists(litebits_script):
        litebits_script = os.path.join(BASE_DIR, "litebits", "farmer.py")
    subprocess.run([PYTHON_BIN, litebits_script, "--once"])

if __name__ == "__main__":
    run_once()
