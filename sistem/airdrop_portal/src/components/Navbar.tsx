export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 bg-obsidian-950/85 backdrop-blur-md border-b border-obsidian-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-ton to-amethyst flex items-center justify-center font-black text-white text-lg shadow-md shadow-ton/20">
            ▲
          </div>
          <div>
            <div className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              Airdrop Portal
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amethyst/15 text-amethyst border border-amethyst/25">
                TON Web3
              </span>
            </div>
            <div className="text-[11px] text-slate-400">Telegram Miner & Airdrop Directory</div>
          </div>
        </div>

        {/* Status / Quick Stats */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-300 bg-obsidian-850 px-3 py-1.5 rounded-lg border border-obsidian-700">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-semibold text-white">26</span> Active Bots
          </div>

          <a
            href="#catalog"
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-obsidian-800 hover:bg-obsidian-700 border border-obsidian-700 text-slate-200 transition-colors"
          >
            Browse Catalog
          </a>
        </div>
      </div>
    </header>
  );
}
