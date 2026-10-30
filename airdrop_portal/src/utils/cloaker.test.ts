import { describe, it, expect, vi } from 'vitest';
import { getAirdropBySlug, getAirdropsList, getCloakedPath, launchAirdrop } from './cloaker';

describe('Cloaker Utility & Data Integrity', () => {
  it('should list all verified airdrops without excluded scam items', () => {
    const list = getAirdropsList();
    expect(list.length).toBe(26);

    const ids = list.map((item) => item.id);
    expect(ids).not.toContain('mrg');
    expect(ids).not.toContain('victor');
    expect(ids).toContain('crownminer');
    expect(ids).toContain('grambuddies');
  });

  it('should find an airdrop by slug', () => {
    const item = getAirdropBySlug('crownminer');
    expect(item).toBeDefined();
    expect(item?.name).toBe('Crown Miner');
    expect(item?.chain).toBe('TON');
  });

  it('should return undefined for invalid slug', () => {
    const item = getAirdropBySlug('invalid-non-existent-slug');
    expect(item).toBeUndefined();
  });

  it('should generate a clean cloaked URL path', () => {
    const path = getCloakedPath('diggo');
    expect(path).toBe('#/go/diggo');
  });

  it('should trigger window.open with security attributes on launch', () => {
    const openMock = vi.fn();
    vi.stubGlobal('window', { open: openMock });

    const dummyItem = {
      id: 'test',
      name: 'Test Miner',
      symbol: 'TEST',
      chain: 'TON',
      ecosystem: 'Test',
      status: 'Active Farming' as const,
      payoutInfo: 'Instant',
      description: 'Desc',
      botHandle: '@TestBot',
      referralUrl: 'https://t.me/TestBot?start=ref_123',
      slug: 'test'
    };

    launchAirdrop(dummyItem);
    expect(openMock).toHaveBeenCalledWith(
      'https://t.me/TestBot?start=ref_123',
      '_blank',
      'noopener,noreferrer'
    );
  });
});
