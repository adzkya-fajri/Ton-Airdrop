# Telegram Mini-App Cluster Architecture & Hierarchy

This document provides a comprehensive architectural breakdown of the farming hub. The ecosystem organizes 161+ registered Telegram bots into 5 distinct execution clusters managed by unified multi-tenant runners and background daemons.

---

## 🏛️ System Architecture Overview

```
                      +-----------------------------+
                      |   Telegram API / MTProto    |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                                           |
+--------------v---------------+             +-------------v--------------+
|   auth_generator (Daemon)    |             |    airdrop_portal (Vite)   |
|   Auto-refreshes initData    |             |   3D WebGL Live Dashboard  |
+--------------+---------------+             +----------------------------+
               |
               +-----------------------+-----------------------+
               |                       |                       |
+--------------v--------+    +---------v-----------+    +------v--------------+
|   Unified Runners     |    | Standalone Farmers  |    |  Supabase Edge      |
|   (5 Multi-Tenant)    |    | (44 Custom Python)  |    |  Multi-Bot Miners   |
+-----------------------+    +---------------------+    +---------------------+
```

---

## 📦 Cluster Hierarchy & Classification

The bots are partitioned into 5 core clusters based on protocol, API mechanism, and gameplay pattern:

### Cluster 1: CryptoBot & Direct Payment Mini-Apps
- **Runner**: `runners/cryptobot_runner.py`
- **Characteristics**: Instant micro-payouts directly into `@CryptoBot`, FaucetPay, or TON on-chain wallets.
- **Key Bots**:
  - `tonclick` (TON Click Robot)
  - `litebits` (LiteBits Bitcoin Lightning Faucet)
  - `trxminer` (TRX Miner Beta)
  - `boxtrust` (BoxTrust Multi-Faucet)
  - `dogsgalaxyrobot`, `adclickersbot`, `toptokenofficialbot`, `taskclicksbot`

### Cluster 2: Ad-Task & PTC Click Networks
- **Runner**: `runners/adtask_runner.py`
- **Characteristics**: Paid-to-click (PTC), sponsored channel verification, web visit tasks, and ad-watching pipelines.
- **Key Bots**:
  - `clickbee` (ClickBee Network: LTC, TRX, DOGE)
  - `starnex` (StarNex Lottery)
  - `bplwalletbot`, `yaojingappbot`, `honeyantsbot`, `emojifyearnbot`

### Cluster 3: Mini-Empire & Idle Tycoon GameFi
- **Runner**: `runners/miniempire_runner.py`
- **Characteristics**: Idle empire mechanics, energy regeneration, passive warehouse production, and multi-tier building upgrades.
- **Key Bots**:
  - `crownminer` (Crown Miner: Ore, Gold, Shards, Depth Chests)
  - `crownville` (Crownville Kingdom: City Builder & Resource Guilds)
  - `chickenempire` (Chicken Empire: Egg production, slot booster)
  - `goldkeepers` (Gold Keepers)
  - `deepmine` (Deep Mine)
  - `staticvein` (Static Vein 2.0)
  - `minerxrealm` (MinerXRealm)

### Cluster 4: DEX, Swaps & Multi-Pool Liquidity
- **Runner**: `runners/dex_runner.py`
- **Characteristics**: Decentralized exchange simulation, token swaps, liquidity farming, and stake harvesting.
- **Key Bots**:
  - `tomarket` (Tomarket: Tomato drop, daily combo harvest)
  - `clayton` (Clayton Game: 512 game, stack game, daily check-in)
  - `catopia` (Catopia Game: Cat leveling, fishing mini-game)
  - `metafarming` (Meta Farming)
  - `nautilus` (Nautilus Mine)
  - `thunderwaves` (Thunder Waves)

### Cluster 5: Telegram Native & MTProto Chat Farmers
- **Runner**: `runners/tgnative_runner.py`
- **Characteristics**: Interacts directly with Telegram bots using native MTProto messages, button callbacks, and inline queries.
- **Key Bots**:
  - `babyyoda` (Baby Yoda: Daily galactic war claim)
  - `slaylands` (SlayLands RPG: Dungeon loot)
  - `robotempire` (Robot Empire: Re-charge and mining)
  - `mininggram` (Mining GRAM: Hashrate boost and token harvest)
  - `odra` (ODRA Mining)

---

## 🛠️ Core Infrastructure Daemons

### 1. Unified Multi-Tenant Runners (`sistem/runners/`)
Consolidates 130+ bots that share identical execution workflows into 5 asynchronous runners. Each runner:
- Isolates exceptions so single-bot network timeouts never crash other workers.
- Implements randomized jitter delays (3 to 7 seconds) to respect Telegram API FloodWait limits.
- Uses thread pools and async event loops to minimize CPU and memory footprint.

### 2. Batch Credential Refresher (`sistem/auth_generator/`)
- Interacts with Telegram MTProto via Telethon using read-only session clones.
- Periodically requests fresh `initData` parameters for Mini-Apps requiring fresh cryptographic HMAC signatures.
- Automatically writes updated tokens into individual `config.json` files without human intervention.

### 3. Health & Maintenance Engine (`sistem/maintenance/`)
- `deadbot_detector.py`: Scans response codes and logs to identify inactive, rugpulled, or closed bots.
- `promo_claimer.py`: Automatically redeems seasonal promotional codes across supported bots.
- `log_rotator.py`: Compresses and truncates log files to maintain optimal disk usage.
