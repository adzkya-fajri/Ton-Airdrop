# 🌾 MASTER REGISTRY & DOKUMENTASI TELEGRAM AUTO-FARMERS

Dokumentasi ini adalah **peta rujukan utama** untuk seluruh bot farming dan mining Telegram yang berjalan di direktori ini.  
> **Tujuan:** Memudahkan pencarian isian, pemetaan endpoint API, struktur autentikasi, status service background, dan hierarki ekosistem tanpa perlu membuang banyak context token.  
> Mesin terstruktur (JSON): lihat [`REGISTRY.json`](./REGISTRY.json).

---

## 🧭 DAFTAR PEMETAAN LENGKAP 20 BOT FARMER

| No | Folder | Nama Bot | Handle Telegram | WebApp URL | Service Linux (`systemd --user`) | Tipe Auth / Primary Key | API Base URL |
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

## 🤝 HIERARKI EKOSISTEM GRAM BUDDIES (TON)

```
                     ┌────────────────────────────────────────┐
                     │          🤝 GRAM BUDDIES NETWORK       │
                     └───────────────────┬────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
         [ Gram Buddies 💎 ]                       [ CHICKEN Empire 🐔 ]
       • Bot: `@GramBuddiesBot`                  • Bot: `@chicken_empirebot`
       • Folder: `farmers/grambuddies/`          • Folder: `farmers/chickenempire/`
       • Tambang GEMS & Points                   • Produksi Telur, CORN Power, Slot Spin
       • WD Terbukti: Paid ke TON Wallet         • WD Terhubung langsung ke dompet TON & GB
```

---

## 👑 HIERARKI EKOSISTEM CROWNVILLE CORP

```
                         ┌────────────────────────────────────────┐
                         │          👑 CROWNVILLE CORP            │
                         └───────────────────┬────────────────────┘
                                             │
        ┌────────────────────────────────────┼────────────────────────────────────┐
        ▼                                    ▼                                    ▼
  [ Crownville 🏰 ]                  [ Crown Miner ⛏️ ]                   [ Basilisk 🐉 ]
• Role: Induk (Kerajaan & Pasar P2P) • Role: Tambang Bawah Tanah          • Role: Peternak Naga & Telur
• Folder: `farmers/crownville/`      • Folder: `farmers/crownminer/`      • WebApp: `app.basilisk...`
• Panen Emas, Makanan, Bijih, Kayu   • Shards, Emas, Bijih, Koin CROWN    • Sinergi: Boost Hashrate Miner
• Service: `crownville-farmer`       • Service: `crownminer-farmer`       • API: `/api/xgame`
                                             │
        ┌────────────────────────────────────┴────────────────────────────────────┐
        ▼                                                                         ▼
 [ Crownville Survivors 🎮 ]                                               [ Crown Lands 🗺️ ]
• Role: Web3 Survival Action                                              • Role: Pemilikan Lahan Terbuka
• Handle: `@CrownvilleSurvivorsBot`                                       • Handle: `@CrownLandsBot`
• Status: ⏳ Presale Founder Pack                                         • Status: ⏳ Presale Tanah
```

### Karakteristik Penting Crownville:
1. **Auto-Payout Real CROWN:** Terhubung ke TON Wallet (`autopay: True`). Begitu akumulasi mencapai **≥ 100 CROWN**, server mengirimkan koin langsung ke wallet TON harian pukul 19:30 UTC.
2. **Transfer Sumber Daya Antar Game:** Bijih & Emas dari Crown Miner ditransfer ke kota Crownville via `/api/game/withdraw`.
3. **Cross-Game Sinergi:** Telur Basilisk dikirim ke miner (`/api/golden/send-miner`) untuk melipatgandakan kecepatan kedalaman galian.

---

## ⚡ DAEMON PENYEGAR TOKEN OTOMATIS (`auth_generator`)

* **Lokasi Folder:** `farmers/auth_generator/`
* **File Utama:** `generator.py`
* **Session Telethon:** `tg_session.session` (Menggunakan MTProto resmi untuk bypass kadaluarsa `initData`)
* **Interval Siklus:** Setiap **25 menit** (1500 detik) otomatis mengambil `initData` baru dan menginjeksi ke masing-masing `config.json` bot.
* **Perintah Uji Manual Satu Siklus:**
  ```bash
  cd /run/media/splev/38a4cd13-11cc-4381-81a9-76765c1a286e1/farmers/auth_generator
  source venv/bin/activate
  python3 generator.py --once
  ```

---

## 🛠️ PANDUAN PERINTAH OPERASIONAL (CHEAT SHEET)

### 1. Cek Status Service Tertentu
```bash
systemctl --user status <nama-service>.service
# Contoh:
systemctl --user status crownville-farmer.service
systemctl --user status crownminer-farmer.service
```

### 2. Restart / Reload Service Farmer
```bash
systemctl --user restart <nama-service>.service
```

### 3. Pantau Log Aktivitas Real-time
```bash
tail -f /run/media/splev/38a4cd13-11cc-4381-81a9-76765c1a286e1/farmers/<folder>/farmer.log
# Contoh pantau Crownville:
tail -f /run/media/splev/38a4cd13-11cc-4381-81a9-76765c1a286e1/farmers/crownville/farmer.log
```

### 4. Restart Bot Telegram Monitoring (`tele-bot`)
```bash
docker restart tele-bot
docker logs tele-bot --tail 30
```

---

## 📂 STRUKTUR STANDAR SETIAP FOLDER FARMER
Setiap folder farmer memiliki struktur seragam berikut:
```text
farmers/<nama-bot>/
├── config.json    # Konfigurasi token (init_data / token), parameter interval, toggle fitur
├── farmer.py      # Engine loop otomatisasi klaim, tap, harvest, dan keepalive
└── farmer.log     # Riwayat logging status, hasil panen, hashrate, dan saldo
```
# Ton-Airdrop
# Ton-Airdrop
# Ton-Airdrop
# Ton-Airdrop
