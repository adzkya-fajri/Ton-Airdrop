import { ExternalLink, Info, CheckCircle2 } from 'lucide-react';
import { AirdropItem } from '../types/airdrop';
import { launchAirdrop } from '../utils/cloaker';

interface AirdropCardProps {
  item: AirdropItem;
  onOpenDetail: (item: AirdropItem) => void;
}

export default function AirdropCard({ item, onOpenDetail }: AirdropCardProps) {
  const getStatusBadge = (status: AirdropItem['status']) => {
    switch (status) {
      case 'Auto-Payout':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Auto Payout
          </span>
        );
      case 'Mining Pool':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amethyst/15 text-amethyst border border-amethyst/30">
            Mining Pool
          </span>
        );
      case 'Multi-Crypto':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-amber-950/60 text-amber-300 border border-amber-800/40">
            Multi-Crypto
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-sky-950/60 text-sky-300 border border-sky-800/40">
            Active Farming
          </span>
        );
    }
  };

  return (
    <div className="group relative bg-obsidian-800/90 hover:bg-obsidian-800 border border-obsidian-700 hover:border-amethyst/50 rounded-2xl p-5 flex flex-col justify-between transition-all duration-200 hover:shadow-xl hover:shadow-amethyst/5">
      <div>
        {/* Header: Name & Status */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-white text-base group-hover:text-amethyst transition-colors">
                {item.name}
              </h3>
              {item.highlight && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-ton/20 text-sky-300 border border-ton/30">
                  TOP
                </span>
              )}
            </div>
            <div className="text-xs font-medium text-slate-400 mt-0.5">{item.botHandle}</div>
          </div>
          {getStatusBadge(item.status)}
        </div>

        {/* Token Symbol & Ecosystem */}
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-obsidian-700 text-slate-200">
            {item.symbol}
          </span>
          <span className="text-xs text-slate-400 bg-obsidian-850 px-2 py-0.5 rounded-md border border-obsidian-700">
            {item.ecosystem}
          </span>
          <span className="text-xs font-semibold text-ton ml-auto">
            {item.chain}
          </span>
        </div>

        {/* Description */}
        <p className="text-xs text-slate-300 leading-relaxed line-clamp-2 mb-4">
          {item.description}
        </p>

        {/* Payout Snippet */}
        <div className="flex items-center gap-2 p-2.5 rounded-xl bg-obsidian-850/80 border border-obsidian-700/80 text-[11px] text-slate-300 mb-5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span className="truncate">{item.payoutInfo}</span>
        </div>
      </div>

      {/* Action Buttons with 44px minimum tap targets */}
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-obsidian-700/50">
        <button
          onClick={() => onOpenDetail(item)}
          className="w-full min-h-[44px] inline-flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-obsidian-700 hover:bg-obsidian-700/80 text-slate-200 text-xs font-semibold transition-colors"
        >
          <Info className="w-3.5 h-3.5" />
          Details
        </button>

        <button
          onClick={() => launchAirdrop(item)}
          className="w-full min-h-[44px] inline-flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-amethyst hover:bg-amethyst-hover text-white text-xs font-semibold transition-colors shadow-sm shadow-amethyst/30"
        >
          <span>Open Bot</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
