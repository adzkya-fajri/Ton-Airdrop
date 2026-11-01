# 🌐 Telegram Airdrop & Farmer Hub (`airdrop_portal`)

A modern, high-performance web directory built with React 18, TypeScript, Tailwind CSS, and Three.js. Features a dark slate and obsidian aesthetic with subtle purple amethyst accents, designed to showcase 26 verified mining bots and airdrop MiniApps across The Open Network (TON) Web3 ecosystem.

## ✨ Key Features

- **Interactive 3D TON Coin Canvas:** Real-time WebGL rendering of the official The Open Network coin with kinetic orbital rings, smooth floating animations, and responsive cursor and touch parallax. Features an automated SVG fallback for devices lacking WebGL support.
- **Referral Link Cloaking:** Shields raw Telegram invite parameters (`?start=ref_...`) behind an internal router (`#/go/:slug` and clean direct action buttons), providing a seamless and professional user journey.
- **Real-Time Filtering & Instant Search:** Fast multi-category filtering (Crownville Corp, Gram Buddies, Telegram MiniApps, Cloud Mining, Mining Pool, Multi-Crypto) combined with instant keyword search across bot names, tokens, handles, and ecosystem tags.
- **Anti-Slop & WCAG AA Compliant:** High contrast ratios, no generic AI placeholders, accessible keyboard navigation (`Escape` key modal dismissal), and touch-friendly targets (minimum 44x44px).

---

## 🚀 Getting Started

### 1. Run Development Server
Navigate to the `airdrop_portal` directory and start the local development server:
```bash
cd airdrop_portal
pnpm install
pnpm run dev
```
Open your browser at `http://localhost:5173`.

### 2. Production Build
To create an optimized production build:
```bash
cd airdrop_portal
pnpm run build
```
Static production files will be output to the `dist/` directory.

### 3. Run Test Suite
Run unit tests with Vitest:
```bash
cd airdrop_portal
pnpm run test
```

---

## 📝 Customizing Referral Links

All bot records, handles, and referral links are centrally configured in:
[`src/data/airdrops.json`](./src/data/airdrops.json)

Each entry follows this structure:
```json
{
  "id": "crownminer",
  "name": "Crown Miner",
  "symbol": "CROWN / GOLD",
  "chain": "TON",
  "ecosystem": "Crownville Corp",
  "status": "Auto-Payout",
  "payoutInfo": "Automatic daily transfer to TON Wallet upon reaching minimum balance of 100 CROWN.",
  "description": "Subterranean resource mining, gold flakes, ores, and decentralized CROWN tokens.",
  "botHandle": "@CrownMinerBot",
  "referralUrl": "https://t.me/CrownMinerBot?start=YOUR_REFERRAL_CODE",
  "slug": "crownminer",
  "highlight": true
}
```

Simply update the `"referralUrl"` value with your personal Telegram invite link. The user interface will present a clean "Open Bot" action without showing raw referral parameters in the card view.

---

## 🛡️ Security & Anti-Scam Policy

Projects `mrg` (MRG Miner) and `victor` (Victor's Company) are explicitly excluded from this directory due to security risks and community scam flags.
