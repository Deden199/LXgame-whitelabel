import React, { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';

export default function SpotlightSlider({ games = [], onLaunch }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const reduceMotion = useMemo(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches, []);

  useEffect(() => {
    if (reduceMotion || paused || games.length <= 1) return undefined;
    const timer = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % games.length);
    }, 3600);

    return () => window.clearInterval(timer);
  }, [games.length, paused, reduceMotion]);

  useEffect(() => {
    if (activeIndex > games.length - 1) setActiveIndex(0);
  }, [games.length, activeIndex]);

  if (!games.length) return null;

  return (
    <section className="spotlight-slider section-enter" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={() => setPaused(false)}>
      <div className="spotlight-track" style={{ transform: `translateX(-${activeIndex * 100}%)` }}>
        {games.map((game) => (
          <article key={game.id} className="spotlight-slide" onClick={() => onLaunch(game)}>
            <img src={game.thumbnail_url || '/placeholder-game.svg'} alt={game.name} className="spotlight-image" />
            <div className="spotlight-overlay">
              <p className="text-xs uppercase tracking-wider text-primary-foreground/80">Spotlight</p>
              <h3 className="text-lg font-bold text-primary-foreground">{game.name}</h3>
              <p className="text-xs text-primary-foreground/80">{game.provider_name || game.provider_id}</p>
            </div>
          </article>
        ))}
      </div>

      <Button type="button" variant="outline" size="icon" className="spotlight-nav spotlight-nav-left" onClick={() => setActiveIndex((prev) => (prev - 1 + games.length) % games.length)} aria-label="Slide sebelumnya">
        <ChevronLeft className="w-4 h-4" />
      </Button>
      <Button type="button" variant="outline" size="icon" className="spotlight-nav spotlight-nav-right" onClick={() => setActiveIndex((prev) => (prev + 1) % games.length)} aria-label="Slide berikutnya">
        <ChevronRight className="w-4 h-4" />
      </Button>

      <div className="spotlight-dots">
        {games.map((game, idx) => (
          <button key={game.id} type="button" className={`spotlight-dot ${idx === activeIndex ? 'is-active' : ''}`} onClick={() => setActiveIndex(idx)} aria-label={`Pindah ke slide ${idx + 1}`} />
        ))}
      </div>
    </section>
  );
}
