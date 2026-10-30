# 🌐 Telegram Airdrop & Farmer Hub (`airdrop_portal`)

Aplikasi web modern bertema gelap (*obsidian*) dengan aksen ungu (*amethyst*) dan biru TON (*The Open Network*) untuk menampilkan katalog 26 bot miner dan airdrop terverifikasi dari ekosistem Telegram Web3.

Dilengkapi dengan:
- **Hero 3D TON Coin Canvas:** Render 3D koin resmi TON interaktif dengan pencahayaan dinamis dan cincin orbital kinetik berbasis Three.js.
- **Referral Link Cloaking:** Tautan referral Anda diselubungi secara elegan melalui router internal (`#/go/:slug` atau tombol aksi langsung "Buka Bot"), tanpa mengekspos parameter invite mentah (`?start=ref_...`) di kartu antarmuka.
- **Filter & Search Realtime:** Filter instan berdasarkan kategori ekosistem (Crownville Corp, Gram Buddies, Telegram MiniApps, Cloud Mining, Multi-Crypto) dan pencarian kata kunci.
- **Desain Bebas Slop (Anti-Slop Compliant):** Memenuhi standar WCAG AA (kontras teks tinggi), bebas dari klise AI, dan ramah aksesibilitas keyboard (modal dapat ditutup dengan tombol `Escape`).

---

## 🚀 Cara Menjalankan

### 1. Menjalankan Server Pengembangan (Dev Server)
Masuk ke direktori `airdrop_portal` dan jalankan:
```bash
cd farmers/airdrop_portal
pnpm run dev
```
Buka browser pada alamat `http://localhost:5173`.

### 2. Membangun Versi Produksi (Production Build)
```bash
cd farmers/airdrop_portal
pnpm run build
```
Aset statis siap di-deploy akan dihasilkan pada folder `dist/`.

### 3. Menguji Suite Unit Test
```bash
cd farmers/airdrop_portal
pnpm run test
```

---

## 📝 Cara Menyesuaikan Link Referral Anda

Seluruh daftar bot dan tautan referral tersimpan secara terpusat pada file:
[`src/data/airdrops.json`](./src/data/airdrops.json)

Setiap entri bot memiliki struktur:
```json
{
  "id": "crownminer",
  "name": "Crown Miner",
  "symbol": "CROWN / GOLD",
  "chain": "TON",
  "ecosystem": "Crownville Corp",
  "status": "Auto-Payout",
  "payoutInfo": "Kirim otomatis harian ke TON Wallet saat saldo mencapai minimal 100 CROWN.",
  "description": "Penambangan sumber daya bawah tanah, serpihan emas, bijih, dan token CROWN terdesentralisasi.",
  "botHandle": "@CrownMinerBot",
  "referralUrl": "https://t.me/CrownMinerBot?start=KODE_REFERRAL_ANDA",
  "slug": "crownminer",
  "highlight": true
}
```

Cukup ubah field `"referralUrl"` pada bot yang ingin Anda kaitkan dengan akun referral Telegram pribadi Anda. Pengunjung web hanya akan melihat tombol bersih "Buka Bot" tanpa mengetahui tautan tersebut merupakan invite link.

---

## 🛡️ Kebijakan Keamanan & Anti-Scam
Proyek `mrg` (MRG Miner) dan `victor` (Victor's Company) secara eksplisit dikecualikan dari katalog ini atas pertimbangan keamanan dan risiko label scam.
