# 🌾 Telegram Mini-App & Airdrop Automation Hub

A modular, multi-tenant automation ecosystem and real-time WebGL operations portal managing 174+ Telegram Mini-Apps, GameFi ecosystems, and airdrop claim protocols.

[![Live WebGL Portal Demo](https://img.shields.io/badge/Demo-Vercel%20Live-black?style=for-the-badge&logo=vercel)](https://ton-airdrop-black.vercel.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Vite + React 18](https://img.shields.io/badge/Frontend-Vite%20%7C%20React%20%7C%20Three.js-61DAFB?style=for-the-badge&logo=react)](https://vitejs.dev)

---

## 🌐 Live WebGL 3D Portal

Explore the real-time 3D dashboard displaying interactive constellation nodes, live telemetry, and cluster statistics:
- **Interactive Live Demo**: [https://ton-airdrop-black.vercel.app/](https://ton-airdrop-black.vercel.app/)
- **Features**: Three.js particle universe, cluster filtering, real-time APY calculation, and bot health audits.

---

## 📂 Repository Directory Structure

```
ton-airdrop-clean/
├── .env.example               # Environment variables configuration template
├── .gitignore                 # Strict rules excluding secrets, sessions, and logs
├── requirements.txt           # Python dependencies
├── README.md                  # Master project documentation
│
├── docs/                      # Comprehensive technical documentation
│   ├── ARCHITECTURE_AND_CLUSTERS.md   # Complete 6-cluster taxonomy and architecture
│   ├── BOT_AUDIT_AND_RATINGS.md       # Audit reports for 134 verified bots
│   └── MINIAPP_AUTOMATION_GUIDE.md    # Deployment and runtime execution manual
│
└── sistem/                    # Core automation runtime and engines
    ├── REGISTRY.json          # Master JSON database of all 174 registered bots
    ├── run_new_farmers.py     # Single-cycle test runner orchestrator
    │
    ├── runners/               # Unified multi-tenant asynchronous engines
    │   ├── cryptobot_runner.py    # Cluster 1: CryptoBot & instant payment bots
    │   ├── adtask_runner.py       # Cluster 2: Ad-Task & PTC click networks
    │   ├── miniempire_runner.py   # Cluster 3: Mini-Empire idle tycoon bots
    │   ├── dex_runner.py          # Cluster 4: DEX, swaps & multi-pool miners
    │   └── tgnative_runner.py     # Cluster 5: Telegram Native MTProto chat bots
    │
    ├── maintenance/           # Health monitoring & utility daemons
    │   ├── deadbot_detector.py    # Automatic dead and rugpull bot detection
    │   ├── promo_claimer.py       # Seasonal promo code redemption engine
    │   └── log_rotator.py         # Automated log compression and rotation
    │
    ├── auth_generator/        # Batch credential refresher daemon
    │   ├── generator.py           # Background initData token refresh worker
    │   └── login_interactive.py   # MTProto session authentication wizard
    │
    ├── supabase_miners/       # Multi-tenant Supabase Edge Functions miners
    ├── airdrop_portal/        # Vite + React 18 + Tailwind + Three.js web app
    │
    └── <bot_folders>/         # 160+ modular bot directories (e.g. crownminer, clickbee)
        ├── config.json        # Sanitized bot parameters and configuration
        └── farmer.py          # Dedicated automation script (where applicable)
```

---

## 🧩 The 5 Operational Clusters

| Cluster | Primary Focus | Runner Engine | Sample Bots |
|---|---|---|---|
| **Cluster 1: CryptoBot** | Instant micro-payouts to CryptoBot & FaucetPay | `cryptobot_runner.py` | `tonclick`, `litebits`, `trxminer`, `boxtrust` |
| **Cluster 2: AdTask** | PTC visits, sponsor channel verification | `adtask_runner.py` | `clickbee`, `starnex`, `bplwalletbot` |
| **Cluster 3: MiniEmpire** | Idle GameFi, energy taps, depth chests | `miniempire_runner.py` | `crownminer`, `crownville`, `chickenempire`, `deepmine` |
| **Cluster 4: DEX & Swaps** | Multi-pool token swaps and liquidity drops | `dex_runner.py` | `tomarket`, `clayton`, `catopia`, `metafarming` |
| **Cluster 5: TG Native** | MTProto chat games and text mini-apps | `tgnative_runner.py` | `babyyoda`, `slaylands`, `robotempire`, `mininggram` |

---

## ⚡ Quick Start

### 1. Clone & Set Up Configuration
```bash
git clone git@github.com:adzkya-fajri/Ton-Airdrop.git
cd Ton-Airdrop

# Create your personal .env from the template
cp .env.example .env
```

Edit `.env` with your Telegram API keys obtained from [my.telegram.org](https://my.telegram.org):
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890
```

### 2. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run a Bot or Cluster Runner
```bash
# Run a specific bot:
python3 sistem/crownminer/farmer.py

# Or launch a unified cluster runner:
python3 sistem/runners/miniempire_runner.py
```

---

## 🔒 Security & Privacy Guarantee

- **Zero Credentials Committed**: Telethon `.session` files, phone numbers, HMAC authentication tokens, and on-chain wallet addresses are excluded via `.gitignore` and sanitized placeholders.
- **Multi-Tenant Configuration**: All sensitive values are loaded dynamically from local `.env` variables or private configuration files.
- **Concurrency Protection**: Isolated session handles and SQLite file locks prevent session file corruption during concurrent MTProto operations.

---

## 📄 License

This repository is distributed under the MIT License. See [LICENSE](LICENSE) for details.
