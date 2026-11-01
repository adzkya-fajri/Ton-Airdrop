export interface AirdropItem {
  id: string;
  name: string;
  symbol: string;
  chain: string;
  ecosystem: string;
  status: 'Active Farming' | 'Auto-Payout' | 'Mining Pool' | 'Multi-Crypto' | 'Maintenance';
  payoutInfo: string;
  description: string;
  botHandle: string;
  referralUrl: string;
  slug: string;
  highlight?: boolean;
}
