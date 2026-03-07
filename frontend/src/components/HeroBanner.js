import React, { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Flame, Play, TrendingUp } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';
import { GameThumbnail, ProviderLogoBadge } from './catalog/CatalogMedia';

const PROVIDER_COLORS = {
  pragmaticplay: ['#FF4C4C', '#FF8C00'],
  pgsoft: ['#8B5CF6', '#EC4899'],
  hacksaw: ['#F97316', '#FACC15'],
  nolimit_city: ['#10B981', '#06B6D4'],
  microgaming: ['#3B82F6', '#8B5CF6'],
  playngo: ['#EAB308', '#F97316'],
  red_tiger: ['#EF4444', '#F97316'],
  evolution: ['#14B8A6', '#22C55E'],
  habanero: ['#EC4899', '#F43F5E'],
  cq9: ['#6366F1', '#8B5CF6'],
  jili: ['#F59E0B', '#EAB308'],
  jdb: ['#84CC16', '#22C55E'],
  playson: ['#0EA5E9', '#3B82F6'],
};

const hasTag = (game, tag) => {
  const target = String(tag).toLowerCase();
  return (game.tags || []).some((value) => String(value).toLowerCase() === target);
};

const HeroBannerCard = ({ game, onLaunch, isActive, position, isDesktop }) => {
  const providerSlug = game.provider_slug || game.providerSlug || 'default';
  const colors = PROVIDER_COLORS[providerSlug] || ['#6366F1', '#8B5CF6'];

  const tagLabel = game.is_hot || hasTag(game, 'Hot')
    ? 'HOT'
    : game.is_new || hasTag(game, 'New')
      ? 'NEW'
      : game.is_popular || hasTag(game, 'Popular')
        ? 'TOP'
        : null;

  const tagColor = tagLabel === 'HOT' ? 'bg-red-500' : tagLabel === 'NEW' ? 'bg-green-500' : 'bg-amber-500';

  return (
    <div
      className={cn(
        'hero-banner-card relative overflow-hidden cursor-pointer transition-all duration-500 ease-out',
        isActive ? 'scale-100 opacity-100 z-10' : 'scale-[0.92] opacity-60 z-0',
        position === 'left' && 'translate-x-[-6%]',
        position === 'right' && 'translate-x-[6%]',
        isDesktop ? 'rounded-[20px]' : 'rounded-2xl'
      )}
      style={{
        background: `linear-gradient(135deg, ${colors[0]} 0%, ${colors[1]} 100%)`,
        flex: isActive ? (isDesktop ? '0 0 68%' : '0 0 78%') : (isDesktop ? '0 0 16%' : '0 0 10%'),
        height: '100%',
        boxShadow: isActive
          ? `0 24px 48px -12px ${colors[0]}50, 0 12px 24px -6px rgba(0,0,0,0.35)`
          : 'none'
      }}
      onClick={() => onLaunch(game)}
      data-testid={`hero-banner-card-${game.id}`}
    >
      <div className="absolute inset-0">
        <GameThumbnail
          game={game}
          className="h-full w-full object-cover"
          wrapperClassName="h-full w-full"
          imageTestId={`hero-banner-image-${game.id}`}
          fallbackTestId={`hero-banner-fallback-${game.id}`}
        />
      </div>
      <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/20 to-black/55" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent" />

      {tagLabel ? (
        <div
          className={cn(
            'absolute font-bold text-white shadow-lg',
            isDesktop ? 'top-6 left-6 px-4 py-2 rounded-lg text-sm' : 'top-3 left-3 px-2 py-0.5 rounded text-[10px]',
            tagColor
          )}
        >
          {tagLabel}
        </div>
      ) : null}

      {isActive && isDesktop ? (
        <div className="absolute top-6 right-6 px-4 py-2 bg-black/60 backdrop-blur-sm rounded-xl">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-sm font-semibold text-white">RTP {game.rtp || 96}%</span>
          </div>
        </div>
      ) : null}

      <div className={cn('absolute bottom-0 left-0 right-0', isDesktop ? 'p-8 xl:p-10' : 'p-4')}>
        <div className="mb-2 flex items-center gap-2">
          <ProviderLogoBadge provider={game} className={cn(isDesktop ? 'h-10 w-10' : 'h-7 w-7', 'rounded-full border-white/20')} />
          <p className={cn('uppercase tracking-wider text-white/75', isDesktop ? 'text-sm xl:text-base' : 'text-[10px]')}>
            {game.provider_name || providerSlug}
          </p>
        </div>
        <h3 className={cn('font-bold text-white mb-2 line-clamp-2 drop-shadow-sm', isDesktop ? 'text-2xl xl:text-3xl max-w-[75%]' : 'text-base max-w-[88%]')}>
          {game.name || game.title}
        </h3>
        {isActive ? (
          <div className={cn('flex items-center mt-4', isDesktop ? 'gap-5' : 'gap-2 mt-3')}>
            <Button
              size={isDesktop ? 'lg' : 'sm'}
              className={cn(
                'font-semibold bg-white text-black hover:bg-white/90 shadow-xl',
                isDesktop ? 'h-12 px-8 text-base rounded-xl' : 'h-8 px-4 text-xs'
              )}
              onClick={(event) => {
                event.stopPropagation();
                onLaunch(game);
              }}
            >
              <Play className={cn(isDesktop ? 'w-5 h-5 mr-2' : 'w-3 h-3 mr-1')} />
              Mainkan Sekarang
            </Button>
            {!isDesktop ? (
              <span className="text-[10px] text-white/65">RTP {game.rtp || 96}%</span>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default function HeroBanner({ games = [], onLaunch }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const checkDesktop = () => setIsDesktop(window.innerWidth >= 1024);
    checkDesktop();
    window.addEventListener('resize', checkDesktop);
    return () => window.removeEventListener('resize', checkDesktop);
  }, []);

  const featuredGames = useMemo(() => {
    return games
      .filter((game) => (game.is_hot || game.is_popular || hasTag(game, 'Hot') || hasTag(game, 'Popular')) && (game.source_banner_url || game.thumbnail_url))
      .slice(0, 8);
  }, [games]);

  useEffect(() => {
    if (activeIndex > featuredGames.length - 1) {
      setActiveIndex(0);
    }
  }, [featuredGames.length, activeIndex]);

  useEffect(() => {
    if (isPaused || featuredGames.length <= 1) return undefined;
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % featuredGames.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [featuredGames.length, isPaused]);

  if (featuredGames.length === 0) return null;

  const prevIndex = (activeIndex - 1 + featuredGames.length) % featuredGames.length;
  const nextIndex = (activeIndex + 1) % featuredGames.length;
  const visibleGames = [
    { game: featuredGames[prevIndex], position: 'left' },
    { game: featuredGames[activeIndex], position: 'center' },
    { game: featuredGames[nextIndex], position: 'right' },
  ];

  return (
    <section
      className={cn('hero-banner-section section-enter relative z-0', isDesktop ? 'mb-10' : 'mb-6')}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      data-testid="hero-banner-section"
    >
      <div className={cn('flex items-center justify-between', isDesktop ? 'mb-6' : 'mb-3')}>
        <div className="flex items-center gap-2.5">
          <div className={cn('rounded-full bg-gradient-to-r from-amber-500 to-red-500 flex items-center justify-center', isDesktop ? 'w-10 h-10' : 'w-6 h-6')}>
            <Flame className={cn(isDesktop ? 'w-5 h-5' : 'w-3 h-3', 'text-white')} />
          </div>
          <h2 className={cn('font-bold', isDesktop ? 'text-xl xl:text-2xl' : 'text-sm')}>Featured Games</h2>
          <span className={cn('text-muted-foreground', isDesktop ? 'text-base' : 'text-[10px]')}>({featuredGames.length})</span>
        </div>
        <div className={cn('flex', isDesktop ? 'gap-3' : 'gap-1')}>
          <Button variant="outline" size="icon" className={cn('rounded-full', isDesktop ? 'h-11 w-11' : 'h-6 w-6')} onClick={() => setActiveIndex((prev) => (prev - 1 + featuredGames.length) % featuredGames.length)}>
            <ChevronLeft className={cn(isDesktop ? 'w-5 h-5' : 'w-3 h-3')} />
          </Button>
          <Button variant="outline" size="icon" className={cn('rounded-full', isDesktop ? 'h-11 w-11' : 'h-6 w-6')} onClick={() => setActiveIndex((prev) => (prev + 1) % featuredGames.length)}>
            <ChevronRight className={cn(isDesktop ? 'w-5 h-5' : 'w-3 h-3')} />
          </Button>
        </div>
      </div>

      <div className="relative flex items-center justify-center gap-3 overflow-hidden" style={{ minHeight: isDesktop ? '280px' : '220px', height: isDesktop ? '300px' : '220px' }}>
        {visibleGames.map(({ game, position }) => (
          <HeroBannerCard key={`${game.id}-${position}`} game={game} onLaunch={onLaunch} isActive={position === 'center'} position={position} isDesktop={isDesktop} />
        ))}
      </div>

      <div className={cn('flex justify-center', isDesktop ? 'gap-2.5 mt-6' : 'gap-1.5 mt-3')}>
        {featuredGames.map((game, idx) => (
          <button
            key={game.id}
            className={cn(
              'rounded-full transition-all duration-300',
              idx === activeIndex
                ? cn('bg-primary', isDesktop ? 'w-10 h-3' : 'w-4 h-1.5')
                : cn('bg-muted-foreground/30 hover:bg-muted-foreground/50', isDesktop ? 'w-3 h-3' : 'w-1.5 h-1.5')
            )}
            onClick={() => setActiveIndex(idx)}
            aria-label={`Featured game ${idx + 1}`}
          />
        ))}
      </div>
    </section>
  );
}
