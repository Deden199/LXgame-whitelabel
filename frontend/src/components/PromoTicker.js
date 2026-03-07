import React, { useEffect, useMemo, useState } from 'react';
import { Flame, Gift, Zap, Sparkles, Crown } from 'lucide-react';

const PROMO_ITEMS = [
  { icon: Flame, text: 'Promo Harian', accent: 'text-orange-400' },
  { icon: Gift, text: 'Bonus VIP', accent: 'text-primary' },
  { icon: Zap, text: 'Withdraw 1–3 hari kerja', accent: 'text-emerald-400' },
  { icon: Sparkles, text: 'Game Baru setiap minggu', accent: 'text-sky-400' },
  { icon: Crown, text: 'Event Turnamen eksklusif', accent: 'text-purple-400' },
];

export default function PromoTicker() {
  const [isPaused, setIsPaused] = useState(false);
  const reduceMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  // Duplicate items for seamless loop
  const items = useMemo(() => [...PROMO_ITEMS, ...PROMO_ITEMS, ...PROMO_ITEMS], []);

  return (
    <div 
      className="promo-ticker-wrapper"
      data-testid="promo-ticker"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div 
        className={`promo-ticker-track ${reduceMotion || isPaused ? 'paused' : ''}`}
        aria-live="off"
      >
        {items.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={`${item.text}-${idx}`} className="promo-ticker-item">
              <span className={`promo-ticker-icon ${item.accent}`}>
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span className="promo-ticker-text">{item.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
