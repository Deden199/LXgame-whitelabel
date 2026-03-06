import React, { useState, useEffect, useMemo } from 'react';
import { Play, Flame, Star, Sparkles, ChevronLeft, ChevronRight, TrendingUp } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

// Provider color mapping for gradient backgrounds
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
  fastspin: ['#A855F7', '#EC4899'],
  playtech: ['#0EA5E9', '#3B82F6'],
  live22: ['#06B6D4', '#14B8A6'],
  onegame: ['#22C55E', '#84CC16'],
};

const HeroBannerCard = ({ game, onLaunch, isActive, position, isDesktop }) => {
  const providerSlug = game.provider_slug || game.providerSlug || 'default';
  const colors = PROVIDER_COLORS[providerSlug] || ['#6366F1', '#8B5CF6'];
  
  const tagLabel = game.is_hot || game.tags?.includes('Hot') ? 'HOT' 
    : game.is_new || game.tags?.includes('New') ? 'NEW'
    : game.is_popular || game.tags?.includes('Popular') ? 'TOP' : null;
  
  const tagColor = tagLabel === 'HOT' ? 'bg-red-500' 
    : tagLabel === 'NEW' ? 'bg-green-500' 
    : 'bg-amber-500';

  return (
    <div 
      className={cn(
        "hero-banner-card relative overflow-hidden cursor-pointer transition-all duration-500 ease-out",
        isActive ? "scale-100 opacity-100 z-10" : "scale-[0.88] opacity-50 z-0",
        position === 'left' && "translate-x-[-8%]",
        position === 'right' && "translate-x-[8%]",
        // TASK 2 - Larger rounded corners for premium desktop feel
        isDesktop ? "rounded-[20px]" : "rounded-2xl"
      )}
      style={{
        background: `linear-gradient(135deg, ${colors[0]} 0%, ${colors[1]} 50%, ${colors[0]}99 100%)`,
        flex: isActive ? (isDesktop ? '0 0 68%' : '0 0 60%') : (isDesktop ? '0 0 16%' : '0 0 20%'),
        // Add explicit height to match parent
        height: '100%',
        boxShadow: isActive 
          ? `0 24px 48px -12px ${colors[0]}50, 0 12px 24px -6px rgba(0,0,0,0.35)` 
          : 'none'
      }}
      onClick={() => onLaunch(game)}
      data-testid="hero-banner-card"
    >
      {/* Animated background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 20% 80%, white 1px, transparent 1px), radial-gradient(circle at 80% 20%, white 1px, transparent 1px)`,
          backgroundSize: '60px 60px'
        }} />
      </div>
      
      {/* Provider watermark - TASK 2: larger on desktop */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className={cn(
          "text-white/8 font-black uppercase tracking-widest select-none",
          isDesktop ? "text-8xl xl:text-9xl" : "text-5xl"
        )}>
          {(game.provider_name || providerSlug).substring(0, 10)}
        </div>
      </div>
      
      {/* Gradient overlay - smoother */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/25 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-r from-black/35 via-transparent to-black/35" />
      
      {/* Tag badge - TASK 2: bigger on desktop */}
      {tagLabel && (
        <div className={cn(
          "absolute font-bold text-white shadow-lg",
          isDesktop ? "top-6 left-6 px-4 py-2 rounded-lg text-sm" : "top-3 left-3 px-2 py-0.5 rounded text-[10px]",
          tagColor
        )}>
          {tagLabel}
        </div>
      )}
      
      {/* RTP badge - desktop only, more prominent */}
      {isActive && isDesktop && (
        <div className="absolute top-6 right-6 px-4 py-2 bg-black/60 backdrop-blur-sm rounded-xl">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-sm font-semibold text-white">RTP {game.rtp || 96}%</span>
          </div>
        </div>
      )}
      
      {/* Game info - TASK 2: scaled up for desktop */}
      <div className={cn(
        "absolute bottom-0 left-0 right-0",
        isDesktop ? "p-8 xl:p-10" : "p-4"
      )}>
        <p className={cn(
          "uppercase tracking-wider text-white/70 mb-1",
          isDesktop ? "text-sm xl:text-base" : "text-[10px]"
        )}>
          {game.provider_name || providerSlug}
        </p>
        <h3 className={cn(
          "font-bold text-white mb-2 line-clamp-1",
          isDesktop ? "text-2xl xl:text-3xl" : "text-base"
        )}>
          {game.name || game.title}
        </h3>
        {isActive && (
          <div className={cn(
            "flex items-center mt-4",
            isDesktop ? "gap-5" : "gap-2 mt-3"
          )}>
            <Button 
              size={isDesktop ? "lg" : "sm"}
              className={cn(
                "font-semibold bg-white text-black hover:bg-white/90 shadow-xl",
                isDesktop ? "h-12 px-8 text-base rounded-xl" : "h-8 px-4 text-xs"
              )}
              onClick={(e) => {
                e.stopPropagation();
                onLaunch(game);
              }}
            >
              <Play className={cn(isDesktop ? "w-5 h-5 mr-2" : "w-3 h-3 mr-1")} />
              Mainkan Sekarang
            </Button>
            {!isDesktop && (
              <span className="text-[10px] text-white/60">
                RTP {game.rtp || 96}%
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default function HeroBanner({ games = [], onLaunch }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  
  // Detect desktop
  useEffect(() => {
    const checkDesktop = () => setIsDesktop(window.innerWidth >= 1024);
    checkDesktop();
    window.addEventListener('resize', checkDesktop);
    return () => window.removeEventListener('resize', checkDesktop);
  }, []);
  
  // Filter to only featured games (Hot/Popular)
  const featuredGames = useMemo(() => {
    return games.filter(g => 
      g.is_hot || g.is_popular || 
      g.tags?.includes('Hot') || g.tags?.includes('Popular')
    ).slice(0, 8);
  }, [games]);
  
  // Auto-rotate
  useEffect(() => {
    if (isPaused || featuredGames.length <= 1) return;
    const timer = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % featuredGames.length);
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
      className={cn(
        "hero-banner-section section-enter",
        isDesktop ? "mb-12" : "mb-6"
      )}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      data-testid="hero-banner-section"
    >
      {/* Header - TASK 2: bigger section header on desktop */}
      <div className={cn(
        "flex items-center justify-between",
        isDesktop ? "mb-6" : "mb-3"
      )}>
        <div className="flex items-center gap-2.5">
          <div className={cn(
            "rounded-full bg-gradient-to-r from-amber-500 to-red-500 flex items-center justify-center",
            isDesktop ? "w-10 h-10" : "w-6 h-6"
          )}>
            <Flame className={cn(isDesktop ? "w-5 h-5" : "w-3 h-3", "text-white")} />
          </div>
          <h2 className={cn(
            "font-bold",
            isDesktop ? "text-xl xl:text-2xl" : "text-sm"
          )}>Featured Games</h2>
          <span className={cn(
            "text-muted-foreground",
            isDesktop ? "text-base" : "text-[10px]"
          )}>({featuredGames.length})</span>
        </div>
        
        {/* Nav buttons - TASK 2: bigger on desktop */}
        <div className={cn("flex", isDesktop ? "gap-3" : "gap-1")}>
          <Button
            variant="outline"
            size="icon"
            className={cn(
              "rounded-full",
              isDesktop ? "h-11 w-11" : "h-6 w-6"
            )}
            onClick={() => setActiveIndex(prev => (prev - 1 + featuredGames.length) % featuredGames.length)}
          >
            <ChevronLeft className={cn(isDesktop ? "w-5 h-5" : "w-3 h-3")} />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className={cn(
              "rounded-full",
              isDesktop ? "h-11 w-11" : "h-6 w-6"
            )}
            onClick={() => setActiveIndex(prev => (prev + 1) % featuredGames.length)}
          >
            <ChevronRight className={cn(isDesktop ? "w-5 h-5" : "w-3 h-3")} />
          </Button>
        </div>
      </div>
      
      {/* Banner carousel - TASK 2: 260-300px height for desktop */}
      <div 
        className="relative flex items-center justify-center gap-3 overflow-hidden" 
        style={{ 
          minHeight: isDesktop ? '280px' : '200px',
          height: isDesktop ? '300px' : '200px'
        }}
      >
        {visibleGames.map(({ game, position }) => (
          <HeroBannerCard
            key={`${game.id}-${position}`}
            game={game}
            onLaunch={onLaunch}
            isActive={position === 'center'}
            position={position}
            isDesktop={isDesktop}
          />
        ))}
      </div>
      
      {/* Dots - TASK 2: bigger on desktop */}
      <div className={cn(
        "flex justify-center",
        isDesktop ? "gap-2.5 mt-6" : "gap-1.5 mt-3"
      )}>
        {featuredGames.map((_, idx) => (
          <button
            key={idx}
            className={cn(
              "rounded-full transition-all duration-300",
              idx === activeIndex 
                ? cn("bg-primary", isDesktop ? "w-10 h-3" : "w-4 h-1.5") 
                : cn("bg-muted-foreground/30 hover:bg-muted-foreground/50", isDesktop ? "w-3 h-3" : "w-1.5 h-1.5")
            )}
            onClick={() => setActiveIndex(idx)}
          />
        ))}
      </div>
    </section>
  );
}
