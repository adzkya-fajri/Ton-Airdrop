import { AirdropItem } from '../types/airdrop';
import rawData from '../data/airdrops.json';

const airdropsList: AirdropItem[] = rawData as AirdropItem[];

export function getAirdropsList(): AirdropItem[] {
  return airdropsList;
}

export function getAirdropBySlug(slug: string): AirdropItem | undefined {
  return airdropsList.find((item) => item.slug.toLowerCase() === slug.toLowerCase());
}

export function getCloakedPath(slug: string): string {
  return `#/go/${slug}`;
}

export function launchAirdrop(item: AirdropItem): void {
  if (typeof window !== 'undefined' && window.open) {
    window.open(item.referralUrl, '_blank', 'noopener,noreferrer');
  }
}
