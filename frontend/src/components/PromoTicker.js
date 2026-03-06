import React, { useMemo } from 'react';

const PROMO_ITEMS = [
  '🔥 Promo Harian',
  '🎁 Bonus VIP',
  '⚡ Withdraw 1–3 hari kerja',
  '🆕 Game Baru setiap minggu',
  '💎 Event Turnamen eksklusif',
];

export default function PromoTicker() {
  const reduceMotion = useMemo(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches, []);

  return (
    <div className="promo-ticker" data-reduced-motion={reduceMotion ? 'true' : 'false'}>
      <div className="promo-ticker-track">
        {[...PROMO_ITEMS, ...PROMO_ITEMS].map((item, idx) => (
          <span key={`${item}-${idx}`} className="promo-ticker-item">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
