# Mini-App Automation & Deployment Guide

This guide describes how to configure, run, and maintain the farming system across local and server environments.

---

## ⚙️ Initial Configuration

### 1. Environment Setup
Copy the environment template and provide your Telegram API credentials:
```bash
cp .env.example .env
nano .env
```

Configure your credentials inside `.env`:
```env
# Telegram API Credentials (Obtain from https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789

# Telegram Account Information
TELEGRAM_PHONE=+1234567890
TELEGRAM_USER_ID=1234567890
TELEGRAM_USERNAME=YourUsername

# Crypto Payout Destinations
TON_WALLET_ADDRESS=UQCFc...
BEP20_USDT_ADDRESS=0xA4d...
FAUCETPAY_EMAIL_OR_ADDRESS=user@example.com
```

### 2. Python Dependencies
Create a virtual environment and install the required libraries:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
*(Dependencies: `telethon`, `requests`, `python-dotenv`, `aiohttp`, `asyncio`)*

---

## 🚀 Running the Automation

### 1. Single Execution Test Cycle
To run a single verification cycle across newly audited bots:
```bash
python3 sistem/run_new_farmers.py
```

### 2. Running Standalone Bot Farmers
Each bot in `sistem/<bot_id>` can be executed independently:
```bash
# Example: Run Crown Miner farmer
python3 sistem/crownminer/farmer.py

# Example: Run ClickBee PTC task worker
python3 sistem/clickbee/farmer.py
```

### 3. Running Unified Cluster Runners
For high efficiency, execute one of the consolidated cluster runners:
```bash
# Cluster 1: CryptoBot & Direct Payment Bots
python3 sistem/runners/cryptobot_runner.py

# Cluster 2: Ad-Task & PTC Click Bots
python3 sistem/runners/adtask_runner.py

# Cluster 3: Mini-Empire GameFi Bots
python3 sistem/runners/miniempire_runner.py

# Cluster 4: DEX & Swaps
python3 sistem/runners/dex_runner.py

# Cluster 5: Telegram Native MTProto Bots
python3 sistem/runners/tgnative_runner.py
```

### 4. Running the WebGL 3D Dashboard Portal
To explore the visual dashboard locally:
```bash
cd sistem/airdrop_portal
pnpm install
pnpm dev
```
Open your browser at `http://localhost:5173/` to view the 3D particle scene and bot cluster analytics.

---

## 🛡️ Security Best Practices

1. **Never commit `.env` or `*.session` files**:
   The `.gitignore` file is strictly configured to prevent binary Telegram sessions and secret keys from ever being committed to Git.
2. **Session Collision Prevention**:
   The unified runners use isolated session instances with file locks to avoid SQLite database concurrency collisions.
3. **Respect Telegram FloodWait**:
   Do not modify runner jitter parameters below 3 seconds. Telegram MTProto enforces temporary IP suspensions when requests are flooded without random delays.
