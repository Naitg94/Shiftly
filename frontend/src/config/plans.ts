export type PlanId = 'FREE' | 'PLUS' | 'PRO';
export type PlanTier = 'GUEST' | 'FREE' | 'PLUS' | 'PRO';

export interface PlanDefinition {
  id: PlanId;
  name: string;
  displayName: string;
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
    badge: 'Current Plan',
    status: 'active',
    tagline: 'Full access during preview',
    description: 'Full access to all Shiftly intelligence and Project Memory capabilities during the preview phase.',
    features: [
      'AI communication analysis',
      'Project Memory workspaces',
      'Search across discussions & decisions',
      'Source evidence alignment',
      'All supported communication sources (WhatsApp ZIP, EML, MBOX, PDF, DOCX, TXT)',
      'Up to 200,000 characters per analysis',
      'Up to 25 MB file upload limit',
      'Full preview access — no monthly analysis quota',
    ],
    ctaText: 'Current Plan',
    ctaDisabled: true,
  },
  {
    id: 'PLUS',
    name: 'PLUS',
    displayName: 'Plus',
    badge: 'Coming Soon',
    status: 'coming_soon',
    tagline: 'Higher capacity & throughput',
    description: 'More capacity and advanced capabilities are coming for growing projects.',
    features: [
      'Higher analysis throughput',
      'Expanded project history retention',
      'Advanced export and structured formats',
      'Priority queue processing',
    ],
    ctaText: 'Coming Soon',
    ctaDisabled: true,
  },
  {
    id: 'PRO',
    name: 'PRO',
    displayName: 'Pro',
    badge: 'Coming Soon',
    status: 'coming_soon',
    tagline: 'Teams & organizations',
    description: 'Advanced capabilities for larger teams and organizations are coming.',
    features: [
      'Multi-user shared workspaces',
      'Organization-level governance & access control',
      'Team activity analytics',
      'Dedicated processing throughput',
    ],
    ctaText: 'Coming Soon',
    ctaDisabled: true,
  },
];

export function resolvePlanTier(isAuthenticated: boolean): PlanTier {
  return isAuthenticated ? 'FREE' : 'GUEST';
}
