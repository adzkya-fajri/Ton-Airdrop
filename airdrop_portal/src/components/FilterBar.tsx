import { Search, X } from 'lucide-react';

interface FilterBarProps {
  categories: string[];
  selectedCategory: string;
  onSelectCategory: (category: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onReset: () => void;
  totalResults: number;
}

export default function FilterBar({
  categories,
  selectedCategory,
  onSelectCategory,
  searchQuery,
  onSearchChange,
  onReset,
  totalResults
}: FilterBarProps) {
  return (
    <div id="catalog" className="w-full pt-10 pb-6 scroll-mt-20">
      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between mb-6">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Cari bot, koin (TON, CROWN, GEMS), atau ekosistem..."
            className="w-full pl-10 pr-10 py-2.5 bg-obsidian-850 border border-obsidian-700 rounded-xl text-sm text-white placeholder-slate-400 focus:outline-none focus:border-amethyst focus:ring-1 focus:ring-amethyst transition-all"
            aria-label="Cari Airdrop"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-white"
              aria-label="Hapus kata kunci pencarian"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Counter & Reset */}
        <div className="flex items-center gap-3 text-xs text-slate-400 justify-between md:justify-end">
          <span>Menampilkan <strong className="text-white font-semibold">{totalResults}</strong> bot airdrop</span>
          {(searchQuery || selectedCategory !== 'Semua') && (
            <button
              onClick={onReset}
              className="text-amethyst hover:text-amethyst-hover font-semibold transition-colors flex items-center gap-1"
            >
              <X className="w-3.5 h-3.5" />
              Reset Filter
            </button>
          )}
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        {categories.map((category) => {
          const isActive = selectedCategory === category;
          return (
            <button
              key={category}
              onClick={() => onSelectCategory(category)}
              className={`min-h-[42px] px-4 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-150 border flex items-center ${
                isActive
                  ? 'bg-amethyst text-white border-amethyst shadow-sm shadow-amethyst/30'
                  : 'bg-obsidian-850 hover:bg-obsidian-800 text-slate-300 border-obsidian-700 hover:border-obsidian-700'
              }`}
            >
              {category}
            </button>
          );
        })}
      </div>
    </div>
  );
}
