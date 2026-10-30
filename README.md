# 🌾 MASTER REGISTRY & TELEGRAM AUTO-FARMERS DOCUMENTATION

This documentation serves as the **master reference roadmap** for all Telegram farming, mining, and automation bots running in this workspace.
> **Purpose:** Accelerate credential discovery, API endpoint mapping, authentication schemas, background service states, and ecosystem hierarchies without redundant context overhead.
> Machine-readable structure (JSON): see [`REGISTRY.json`](./REGISTRY.json).
> Web showcase & referral portal: see [`airdrop_portal`](./airdrop_portal).

---

## 🧭 COMPREHENSIVE BOT MAPPING DIRECTORY

| No | Folder | Bot Name | Telegram Handle | WebApp URL | Linux Service (`systemd --user`) | Auth Type / Key | API Base URL |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **`atf`** | ATF Miner | `@ATF_AIRDROP_bot` | `https://atfminers.asloni.online/...` | `atf-farmer.service` | `init_data` | `https://atfminers.asloni.online` |
| 2 | **`crownminer`** | Crown Miner | `@CrownMinerBot` | `https://test.crownville.online/crownminer-stage/game/` | `crownminer-farmer.service` | `init_data` | `https://test.crownville.online/cmapi` |
| 3 | **`crownville`** | Crownville | `@Crownvillebot` | `https://crownville.online/` | `crownville-farmer.service` | `init_data` (`X-Telegram-Init-Data`) | `https://crownville.online` |
| 4 | **`diggo`** | Diggo Miner | `@Diggominer_bot` | `https://app.diggocoin.com/` | `diggo-farmer.service` | `token` (Bearer) | `https://app.diggocoin.com` |
| 5 | **`dram`** | DRAM Miner | `@dramminerbot` | `https://dram.faithton.online/` | `dram-farmer.service` | `token` (Bearer) | `https://dram.faithton.online` |
| 6 | **`epsilon`** | Epsilon | `@Epsiloncrypto_bot` | `https://app.epsilons.io/` | `epsilon-farmer.service` | `token` (Bearer) | `https://api.epsilons.io/api/v1` |
| 7 | **`grambuddies`** | Gram Buddies | `@GramBuddiesBot` | `https://buddies.name.ng/` | `grambuddies-farmer.service` | `init_data` (Bearer) | `https://buddies.name.ng/api` |
| 8 | **`lumetra`** | LumeTRA | `@LUMETRAS_BOT` | `https://app.lumetramine.com/` | `lumetra-farmer.service` | `token` (Bearer) | `https://api.lumetramine.com/api` |
| 9 | **`mainet`** | mAInet | `@mainetbot` | `https://app.mainet.io/` | `mainet-farmer.service` | `token` (Bearer) | `https://api.mainet.io` |
| 10 | **`minex`** | MineX⚡ | `@MineXton_bot` | `https://delist.app/` | `minex-farmer.service` | `init_data` (Bearer) | `https://delist.app/api` |
| 11 | **`mininggram`** | Mining GRAM ⛏️ | `@MiningGRAM_Bot` | `https://mining-gram-worker...workers.dev` | `mininggram-farmer.service` | `session_token` / `init_data` | `https://mining-gram-worker.muhaisin0888.workers.dev` |
| 12 | **`monsterland`** | Monsterland | `@monsterland_bot` | `https://lets.playmonsterland.com/` | `monsterland-farmer.service` | `authorization` (`tma initData`) | `https://lets.playmonsterland.com` |
| 13 | **`mrg`** | MRG Miner | `@mrgminerbot` | `https://app.mrgtoken.xyz/` | `mrg-farmer.service` | `init_data` (JSON body) | `https://mrg.up.railway.app` |
| 14 | **`musicmb`** | Music Mining ($MB) | `@MusicMiningMB_Bot` | `https://music-mining.org/` | `musicmb-farmer.service` | `token` (Bearer) | `https://music-mining.org` |
| 15 | **`odra`** | ODRA Mining | `@ODRAcoinBot` | `https://odra.onrender.com/` | `odra-farmer.service` | `init_data` (Bearer) | `https://odra.onrender.com` |
| 16 | **`pickaxeempire`** | Pickaxe Empire | `@PickaxeEmpireBot` | `https://pxe.up.railway.app/` | `pickaxeempire-farmer.service` | `init_data` (Bearer) | `https://pxe.up.railway.app` |
| 17 | **`tomarket`** | Tomarket | `@Tomarket_ai_bot` | `https://mini-app.tomarket.ai/` | `tomarket-farmer.service` | `access_token` / `init_data` | `https://api-web.tomarket.ai/tomarket-game/v1` |
| 18 | **`victor`** | Victor's Company | `@VictorsCompanybot` | `https://app.victors.company/` | `victor-farmer.service` | `x-human-pass` + `authorization` | `https://server.victors.company` |
| 19 | **`vyq`** | VYQ Miner | `@VYQMiners_bot` | `https://api.vyqminer.top/` | `vyq-farmer.service` | `token` (Bearer) | `https://api.vyqminer.top/api` |
| 20 | **`vyro`** | VYRO Miner | `@vyrodrop_bot` | `https://vyro.run.place/` | `vyro-farmer.service` | `auth` (`tma initData`) | `https://vyro.run.place` |
| 21 | **`chickenempire`** | CHICKEN Empire | `@chicken_empirebot` | `https://app.miniempire.app/miniapp/` | `chickenempire-farmer.service` | `init_data` (JSON Body) | `https://app.miniempire.app/miniapp` |
| 22 | **`minerxrealm`** | MinerXRealm | `@MinerXRealmBot` | `https://minerxrealm.zekobusiness0.workers.dev/` | `minerxrealm-farmer.service` | `init_data` (JSON Body) | `https://minerxrealm.zekobusiness0.workers.dev/api` |
| 23 | **`edgeofempire`** | Edge of Empire | `@EdgeOfEmpireBot` | `https://edgeofempire.club/` | `edgeofempire-farmer.service` | `X-Tg-Init` Header | `https://edgeofempire.club/api` |
| 24 | **`tonclick`** | TON Click Robot | `@TonClickRobot` | N/A (MTProto Native) | `tonclick-farmer.service` | `tonclick_session` (Telethon) | `tg://resolve?domain=TonClickRobot` |
| 25 | **`clickbee`** | ClickBee Multi-Crypto | `@ClickBeeLTCBot` / `@ClickBeeBot` / `@ClickBeeDOGEBot` | N/A (MTProto Native PTC) | `clickbee-farmer.service` | `clickbee_session` (Telethon) | `https://bot.clickbeeads.com` |

---

## 🤝 GRAM BUDDIES ECOSYSTEM HIERARCHY (TON)

```
                     ┌────────────────────────────────────────┐
                     │          🤝 GRAM BUDDIES NETWORK       │
                     └───────────────────┬────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
         [ Gram Buddies 💎 ]                       [ CHICKEN Empire 🐔 ]
        • Bot: `@GramBuddiesBot`                  • Bot: `@chicken_empirebot`
        • Directory: `farmers/grambuddies/`       • Directory: `farmers/chickenempire/`
        • Mining GEMS & Points                    • Egg Production, CORN Power, Slot Spins
        • Verified Payouts to TON Wallet          • Connected directly to TON & GB wallet
```

---

## 👑 CROWNVILLE CORP ECOSYSTEM HIERARCHY

```
                         ┌────────────────────────────────────────┐
                         │          👑 CROWNVILLE CORP            │
                         └───────────────────┬────────────────────┘
                                             │
        ┌────────────────────────────────────┼────────────────────────────────────┐
        ▼                                    ▼                                    ▼
  [ Crownville 🏰 ]                  [ Crown Miner ⛏️ ]                   [ Basilisk 🐉 ]
• Role: Core Kingdom & P2P Market    • Role: Subterranean Mining          • Role: Dragon Breeder & Eggs
• Directory: `farmers/crownville/`   • Directory: `farmers/crownminer/`   • WebApp: `app.basilisk...`
• Harvest Gold, Food, Ore, Timber    • Shards, Gold, Ores, CROWN Tokens   • Synergy: Miner Hashrate Boost
• Service: `crownville-farmer`       • Service: `crownminer-farmer`       • API: `/api/xgame`
                                             │
        ┌────────────────────────────────────┴────────────────────────────────────┐
        ▼                                                                         ▼
 [ Crownville Survivors 🎮 ]                                               [ Crown Lands 🗺️ ]
• Role: Web3 Survival Action                                              • Role: Land Ownership & Parcels
• Handle: `@CrownvilleSurvivorsBot`                                       • Handle: `@CrownLandsBot`
• Status: ⏳ Presale Founder Pack                                         • Status: ⏳ Land Presale
```

### Key Crownville Features:
1. **Automated Real CROWN Payouts:** Connected to TON Wallet (`autopay: True`). Once balance reaches **≥ 100 CROWN**, the server initiates automated direct transfers to the registered TON wallet daily at 19:30 UTC.
2. **Cross-Game Resource Transfers:** Ores and gold from Crown Miner transfer directly to Crownville kingdom via `/api/game/withdraw`.
3. **Cross-Game Synergy:** Basilisk eggs can be sent to the miner (`/api/golden/send-miner`) to multiply excavation depth and speed.

---

## ⚡ AUTOMATED CREDENTIAL REFRESH DAEMON (`auth_generator`)

* **Directory:** `farmers/auth_generator/`
* **Core Script:** `generator.py`
* **Telethon Session:** `tg_session.session` (Official MTProto client session to prevent `initData` expiration)
* **Cycle Interval:** Every **25 minutes** (1500 seconds), automatically fetches fresh `initData` and injects updated headers into each bot's `config.json`.
* **Single Run Command:**
  ```bash
  cd auth_generator
  source venv/bin/activate
  python3 generator.py --once
  ```

---

## 🛠️ OPERATIONAL CHEAT SHEET

### 1. Inspect Service Status
```bash
systemctl --user status <service-name>.service
# Examples:
systemctl --user status crownville-farmer.service
systemctl --user status crownminer-farmer.service
```

### 2. Restart / Reload Farmer Services
```bash
systemctl --user restart <service-name>.service
```

### 3. Monitor Real-Time Service Logs
```bash
tail -f farmers/<bot-folder>/farmer.log
# Example for Crownville:
tail -f farmers/crownville/farmer.log
```

### 4. Restart Telegram Monitoring Bot (`tele-bot`)
```bash
docker restart tele-bot
docker logs tele-bot --tail 30
```

---

## 📂 STANDARD FARMER DIRECTORY STRUCTURE
Each bot directory contains a consistent modular layout:
```text
farmers/<bot-folder>/
├── config.json    # Token configuration (init_data / token), cycle intervals, feature toggles
├── farmer.py      # Automation engine loop for claims, taps, harvests, and keepalives
└── farmer.log     # Real-time operation history, yields, hashrate stats, and wallet balances
```
