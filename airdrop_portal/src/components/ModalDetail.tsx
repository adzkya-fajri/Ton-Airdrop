import { useEffect } from 'react';
import { X, ExternalLink, ShieldCheck, Zap, Layers, Wallet } from 'lucide-react';
import { AirdropItem } from '../types/airdrop';
import { launchAirdrop } from '../utils/cloaker';

interface ModalDetailProps {
  item: AirdropItem | null;
  onClose: () => void;
}

export default function ModalDetail({ item, onClose }: ModalDetailProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!item) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="relative w-full max-w-lg bg-obsidian-850 border border-obsidian-700 rounded-2xl p-6 shadow-2xl text-slate-100 flex flex-col gap-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 id="modal-title" className="text-xl font-bold text-white">
                {item.name}
              </h2>
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-amethyst/20 text-amethyst border border-amethyst/30">
                {item.symbol}
              </span>
            </div>
            <div className="text-xs font-semibold text-ton">{item.botHandle}</div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-obsidian-700 transition-colors"
            aria-label="Tutup dialog (Escape)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Overview List */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-xl bg-obsidian-800 border border-obsidian-700 flex items-center gap-2.5">
            <Layers className="w-4 h-4 text-amethyst shrink-0" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Ekosistem</div>
              <div className="text-xs font-bold text-white">{item.ecosystem}</div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-obsidian-800 border border-obsidian-700 flex items-center gap-2.5">
            <Wallet className="w-4 h-4 text-ton shrink-0" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Jaringan Blockchain</div>
              <div className="text-xs font-bold text-white">{item.chain}</div>
            </div>
          </div>
        </div>

        {/* Description */}
        <div>
          <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            Deskripsi Operasional
          </div>
          <p className="text-sm text-slate-200 leading-relaxed bg-obsidian-800/50 p-3.5 rounded-xl border border-obsidian-700/60">
            {item.description}
          </p>
        </div>

        {/* Payout Mechanism */}
        <div>
          <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Status Pembayaran & Payout
          </div>
          <div className="text-xs text-slate-200 bg-obsidian-800/50 p-3.5 rounded-xl border border-obsidian-700/60 flex items-center justify-between">
            <span>{item.payoutInfo}</span>
            <span className="font-semibold text-emerald-400 shrink-0 ml-2">Terverifikasi</span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-3 px-4 rounded-xl bg-obsidian-700 hover:bg-obsidian-700/80 text-slate-300 font-semibold text-xs transition-colors"
          >
            Tutup (Esc)
          </button>

          <button
            onClick={() => launchAirdrop(item)}
            className="flex-1 inline-flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-amethyst hover:bg-amethyst-hover text-white font-semibold text-xs transition-colors shadow-lg shadow-amethyst/30"
          >
            <span>Buka Bot di Telegram</span>
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
