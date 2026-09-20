export type PlanId = 'FREE' | 'PLUS' | 'PRO';
export type PlanTier = 'GUEST' | 'FREE' | 'PLUS' | 'PRO';

export interface PlanDefinition {
  id: PlanId;
  name: string;
  displayName: string;
  price: number;
  priceDisplay: string;
  badge: string;
  status: 'active' | 'coming_soon';
  tagline: string;
  description: string;
  features: string[];
  ctaText: string;
  ctaDisabled?: boolean;
}

export const PLANS: PlanDefinition[] = [
  {
    id: 'FREE',
    name: 'FREE',
    displayName: 'Free',
    price: 0,
    priceDisplay: '$0',
    badge: 'Current Plan',
    status: 'active',
    tagline: 'Active',
    description: 'Essential communication intelligence and Project Memory workspaces.',
    features: [
      '30 analyses per month',
      'Up to 50,000 characters per analysis',
      '10 MB file upload limit',
      '10 Project Memory workspaces',
      '100 MB Project Memory storage',
      'Supported formats: PDF, DOCX, TXT',
      'Search across discussions & decisions',
      'Source evidence alignment',
    ],
    ctaText: 'Current Plan',
    ctaDisabled: true,
  },
  {
    id: 'PLUS',
    name: 'PLUS',
    displayName: 'Plus',
    price: 1,
    priceDisplay: '$1',
    badge: 'Coming Soon',
    status: 'coming_soon',
    tagline: 'Higher capacity & throughput',
    description: 'Higher capacity and expanded communication formats for active professionals.',
    features: [
      '150 analyses per month',
      'Up to 100,000 characters per analysis',
      '20 MB file upload limit',
      '20 Project Memory workspaces',
      '1 GB Project Memory storage',
      'All communication formats (WhatsApp ZIP, EML, MBOX, PDF, DOCX, TXT)',
      'Search across discussions & decisions',
      'Source evidence alignment',
    ],
    ctaText: 'Coming Soon',
    ctaDisabled: true,
  },
  {
    id: 'PRO',
    name: 'PRO',
    displayName: 'Pro',
    price: 5,
    priceDisplay: '$5',
    badge: 'Coming Soon',
    status: 'coming_soon',
    tagline: 'Teams & power users',
    description: 'Maximum capacity, unlimited analyses, and dedicated throughput for power users.',
    features: [
      'Unlimited analyses per month',
      'Up to 200,000 characters per analysis',
      '25 MB file upload limit',
      '50 Project Memory workspaces',
      '4 GB Project Memory storage',
      'All communication formats (WhatsApp ZIP, EML, MBOX, PDF, DOCX, TXT)',
      'Search across discussions & decisions',
      'Source evidence alignment',
    ],
    ctaText: 'Coming Soon',
    ctaDisabled: true,
  },
];
