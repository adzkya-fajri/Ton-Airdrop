import { useState, useMemo, useEffect } from 'react';
import Navbar from './components/Navbar';
import Hero3D from './components/Hero3D';
import FilterBar from './components/FilterBar';
import AirdropCard from './components/AirdropCard';
import ModalDetail from './components/ModalDetail';
import { getAirdropsList, getAirdropBySlug } from './utils/cloaker';
import { AirdropItem } from './types/airdrop';
import { SearchX, Shield, Sparkles } from 'lucide-react';

const CATEGORIES = [
  'Semua',
  'Crownville Corp',
  'Gram Buddies Network',
  'Telegram MiniApps',
  'Cloud Mining',
  'Mining Pool',
  'Telegram Native PTC',
  'Multi-Crypto'
];

export default function App() {
  const [selectedCategory, setSelectedCategory] = useState('Semua');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeModalItem, setActiveModalItem] = useState<AirdropItem | null>(null);

  const allAirdrops = useMemo(() => getAirdropsList(), []);

  // Filter & Search Engine
  const filteredAirdrops = useMemo(() => {
    return allAirdrops.filter((item) => {
      // Category check
      const matchesCategory =
        selectedCategory === 'Semua' ||
        item.ecosystem === selectedCategory ||
        item.status === selectedCategory;

      // Search check
      const query = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !query ||
        item.name.toLowerCase().includes(query) ||
        item.symbol.toLowerCase().includes(query) ||
        item.botHandle.toLowerCase().includes(query) ||
        item.ecosystem.toLowerCase().includes(query) ||
        item.description.toLowerCase().includes(query);

      return matchesCategory && matchesSearch;
    });
  }, [allAirdrops, selectedCategory, searchQuery]);

  // Handle Cloaked Hash Routing (e.g. #/go/:slug or #/detail/:slug)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      if (!hash) return;

      // Cloaked direct launch route: #/go/:slug (using location.replace to bypass popup blockers)
      const goMatch = hash.match(/^#\/?go\/([a-zA-Z0-9_-]+)/);
      if (goMatch) {
        const slug = goMatch[1];
        const target = getAirdropBySlug(slug);
        if (target) {
          window.location.replace(target.referralUrl);
        }
      }

      // Deep link modal detail: #/detail/:slug
      const detailMatch = hash.match(/^#\/?detail\/([a-zA-Z0-9_-]+)/);
      if (detailMatch) {
        const slug = detailMatch[1];
        const target = getAirdropBySlug(slug);
        if (target) {
          setActiveModalItem(target);
        }
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleResetFilters = () => {
    setSelectedCategory('Semua');
    setSearchQuery('');
  };

  return (
    <div className="min-h-screen bg-obsidian-950 text-slate-100 flex flex-col font-sans">
      {/* Sticky Header */}
      <Navbar />

      {/* Hero with 3D TON Coin */}
      <Hero3D />

      {/* Main Catalog Section */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        {/* Filters */}
        <FilterBar
          categories={CATEGORIES}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onReset={handleResetFilters}
          totalResults={filteredAirdrops.length}
        />

        {/* Airdrop Grid */}
        {filteredAirdrops.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredAirdrops.map((item) => (
              <AirdropCard
                key={item.id}
                item={item}
                onOpenDetail={setActiveModalItem}
              />
            ))}
          </div>
        ) : (
          /* Empty State (Anti-Slop R-27 compliant) */
          <div className="py-16 px-4 text-center bg-obsidian-850 rounded-2xl border border-obsidian-700 my-8">
            <div className="w-12 h-12 rounded-xl bg-obsidian-700 flex items-center justify-center mx-auto mb-4 text-slate-400">
              <SearchX className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">
              Tidak Ada Bot Ditemukan
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mb-5 leading-relaxed">
              Tidak ada bot airdrop yang cocok dengan kata kunci &ldquo;{searchQuery}&rdquo; pada kategori {selectedCategory}.
            </p>
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 rounded-xl bg-amethyst hover:bg-amethyst-hover text-white text-xs font-semibold transition-colors"
            >
              Reset Filter & Cari Ulang
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-obsidian-700 bg-obsidian-900/60 py-10 px-4">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span>Katalog Bot & Airdrop Telegram Terverifikasi</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amethyst" />
              Didukung Jaringan The Open Network (TON)
            </span>
          </div>
        </div>
      </footer>

      {/* Modal Detail Dialog */}
      <ModalDetail
        item={activeModalItem}
        onClose={() => setActiveModalItem(null)}
      />
    </div>
  );
}
