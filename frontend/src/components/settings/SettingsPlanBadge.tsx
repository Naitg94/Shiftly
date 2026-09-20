'use client';

interface SettingsPlanBadgeProps {
  plan?: 'GUEST' | 'FREE' | 'PLUS' | 'PRO' | string;
  className?: string;
}

export default function SettingsPlanBadge({ plan = 'FREE', className = '' }: SettingsPlanBadgeProps) {
  const normalized = (plan || 'FREE').toUpperCase();

  if (normalized === 'PRO') {
    return (
      <span
        className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 uppercase shrink-0 shadow-sm shadow-cyan-500/10 ${className}`}
      >
        PRO
      </span>
    );
  }

  if (normalized === 'PLUS') {
    return (
      <span
        className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/30 uppercase shrink-0 ${className}`}
      >
        PLUS
      </span>
    );
  }

  if (normalized === 'FREE') {
    return (
      <span
        className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase shrink-0 ${className}`}
      >
        FREE
      </span>
    );
  }

  return (
    <span
      className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 border border-slate-700 uppercase shrink-0 ${className}`}
    >
      {normalized}
    </span>
  );
}
